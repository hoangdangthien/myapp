"""State management for Well Intervention (GTM) operations with KMonth DCA."""
import reflex as rx
from collections import Counter
from typing import Optional
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from sqlmodel import String, asc, cast, desc, func, or_, select, delete

from ..models import (
    Intervention, 
    InterventionForecast, 
    HistoryProd, 
    KMonth,
    MAX_FORECAST_VERSIONS
)
from ..utils.dca_utils import (
    arps_exponential,
    arps_decline,
    generate_monthly_dates,
    calculate_elapsed_days,
    calculate_cumulative_production,
    calculate_water_cut,
    run_dca_forecast,
    ForecastPoint,
)


class GTMState(rx.State):
    """State for managing Well Intervention (GTM) data with KMonth DCA.
    
    Uses:
    - pandas date_range with freq="MS" for monthly dates
    - KMonth table for uptime factors (K_int)
    - Arps decline functions (Exponential/Hyperbolic)
    - Cumulative: Qoil = K_int * days_in_month * OilRate
    """
    
    # List of all interventions
    GTM: list[Intervention] = []
    
    # Historical production data from HistoryProd table (last 5 years)
    history_prod: list[dict] = []
    
    # KMonth data cache
    k_month_data: dict = {}
    
    # Data transformed for graph visualization
    gtms_for_graph: list[dict] = []
    
    # Currently selected intervention for editing/viewing
    current_gtm: Optional[Intervention] = None
    
    # Selected ID for chart display
    selected_id: str = ""
    
    # Available IDs for selection
    available_ids: list[str] = []
    
    # Forecast parameters
    forecast_end_date: str = ""
    
    # Forecast results
    forecast_data: list[dict] = []
    
    # Chart data combining actual + forecast
    chart_data: list[dict] = []
    
    # Intervention date for vertical line
    intervention_date: str = ""
    
    # Current forecast version being displayed
    current_forecast_version: int = 0
    
    # Available forecast versions for current intervention
    available_forecast_versions: list[int] = []
    
    # Phase selection for chart
    show_oil: bool = True
    show_liquid: bool = True
    show_wc: bool = True
    
    # Search/filter state
    search_value: str = ""
    selected_field: str = ""
    selected_status: str = ""
    
    # File upload state
    upload_progress: int = 0
    upload_status: str = ""
    
    # Dialog control state
    add_dialog_open: bool = False
    
    # DCA mode (True=Exponential, False=Hyperbolic)
    use_exponential_dca: bool = False  # Intervention uses Hyperbolic by default
    
    def set_add_dialog_open(self, is_open: bool):
        self.add_dialog_open = is_open
    
    def toggle_oil(self, checked: bool):
        self.show_oil = checked
    
    def toggle_liquid(self, checked: bool):
        self.show_liquid = checked
    
    def toggle_wc(self, checked: bool):
        self.show_wc = checked

    def load_k_month_data(self):
        """Load KMonth data from database and cache it."""
        try:
            with rx.session() as session:
                k_records = session.exec(select(KMonth)).all()
                self.k_month_data = {
                    rec.MonthID: {
                        "K_oil": rec.K_oil if rec.K_oil else 1.0,
                        "K_liq": rec.K_liq if rec.K_liq else 1.0,
                        "K_int": rec.K_int if rec.K_int else 1.0,
                        "K_inj": rec.K_inj if rec.K_inj else 1.0
                    }
                    for rec in k_records
                }
        except Exception as e:
            print(f"Error loading KMonth data: {e}")
            self.k_month_data = {i: {"K_oil": 1.0, "K_liq": 1.0, "K_int": 1.0, "K_inj": 1.0} for i in range(1, 13)}

    def load_gtms(self):
        """Load all GTMs from database."""
        try:
            # Load KMonth data first
            self.load_k_month_data()
            
            with rx.session() as session:
                query = select(Intervention)
                if self.search_value:
                    search_value = f"%{str(self.search_value).lower()}%"
                    query = query.where(
                        or_(
                            *[
                                getattr(Intervention, field).ilike(search_value)
                                for field in Intervention.model_fields.keys()
                            ]
                        )
                    )
                self.GTM = session.exec(query).all()
            self.transform_data()
            self.available_ids = [gtm.UniqueId for gtm in self.GTM]
            if self.available_ids and not self.selected_id:
                self.selected_id = self.available_ids[0]
                self.load_production_data()
        except Exception as e:
            print(f"Error loading GTMs: {e}")
            self.GTM = []

    def load_production_data(self):
        """Load production data for selected intervention from HistoryProd table."""
        if not self.selected_id:
            self.history_prod = []
            self.chart_data = []
            return
            
        try:
            five_years_ago = datetime.now() - timedelta(days=5*365)
            
            with rx.session() as session:
                history_records = session.exec(
                    select(HistoryProd).where(
                        HistoryProd.UniqueId == self.selected_id,
                        HistoryProd.Date >= five_years_ago
                    ).order_by(desc(HistoryProd.Date))
                ).all()
                
                self.history_prod = []
                for rec in history_records:
                    oil_rate = rec.OilRate if rec.OilRate else 0.0
                    liq_rate = rec.LiqRate if rec.LiqRate else 0.0
                    wc = calculate_water_cut(oil_rate, liq_rate)
                    
                    self.history_prod.append({
                        "UniqueId": rec.UniqueId,
                        "Date": rec.Date,
                        "OilRate": oil_rate,
                        "LiqRate": liq_rate,
                        "WC": round(wc, 2),
                        "GOR": rec.GOR if rec.GOR else 0.0,
                        "Qgas": rec.Qgas if rec.Qgas else 0.0,
                        "Method": rec.Method if rec.Method else "",
                        "Dayon": rec.Dayon if rec.Dayon else 0.0
                    })
                
                # Load available forecast versions
                forecast_versions = session.exec(
                    select(InterventionForecast.Version).where(
                        InterventionForecast.UniqueId == self.selected_id,
                        InterventionForecast.Version > 0
                    ).distinct()
                ).all()
                self.available_forecast_versions = sorted(forecast_versions)
            
            # Get intervention date
            selected_gtm = next(
                (g for g in self.GTM if g.UniqueId == self.selected_id), None
            )
            if selected_gtm:
                self.intervention_date = selected_gtm.PlanningDate
                self.current_gtm = selected_gtm
            
            if self.available_forecast_versions:
                self.current_forecast_version = max(self.available_forecast_versions)
                self.load_forecast_from_db()
            else:
                self.forecast_data = []
            
            self.update_chart_data()
            
        except Exception as e:
            print(f"Error loading production data: {e}")
            self.history_prod = []
    
    def load_forecast_from_db(self):
        """Load forecast data for current version from database."""
        if not self.selected_id or self.current_forecast_version == 0:
            self.forecast_data = []
            return
            
        try:
            with rx.session() as session:
                forecast_records = session.exec(
                    select(InterventionForecast).where(
                        InterventionForecast.UniqueId == self.selected_id,
                        InterventionForecast.Version == self.current_forecast_version
                    ).order_by(InterventionForecast.Date)
                ).all()
                
                self.forecast_data = [
                    {
                        "date": rec.Date.strftime("%Y-%m-%d") if isinstance(rec.Date, datetime) else str(rec.Date),
                        "oilRate": rec.OilRate,
                        "liqRate": rec.LiqRate,
                        "qOil": rec.Qoil,
                        "qLiq": rec.Qliq,
                        "wc": rec.WC
                    }
                    for rec in forecast_records
                ]
        except Exception as e:
            print(f"Error loading forecast from DB: {e}")
            self.forecast_data = []
    
    def set_forecast_version(self, version: int):
        self.current_forecast_version = version
        self.load_forecast_from_db()
        self.update_chart_data()
    
    def filter_intervention(self, search_value):
        self.search_value = search_value
        self.load_gtms()
    
    def update_chart_data(self):
        """Update chart data combining actual history and forecast with Water Cut."""
        chart_points = []
        
        sorted_history = sorted(self.history_prod, key=lambda x: x["Date"])
        for prod in sorted_history:
            date_val = prod["Date"]
            date_str = date_val.strftime("%Y-%m-%d") if isinstance(date_val, datetime) else str(date_val)
            chart_points.append({
                "date": date_str,
                "oilRate": prod["OilRate"],
                "liqRate": prod["LiqRate"],
                "wc": prod["WC"],
                "type": "actual"
            })
        
        for fc in self.forecast_data:
            wc_forecast = calculate_water_cut(fc["oilRate"], fc["liqRate"])
            
            chart_points.append({
                "date": fc["date"],
                "oilRateForecast": fc["oilRate"],
                "liqRateForecast": fc["liqRate"],
                "wcForecast": round(wc_forecast, 2),
                "type": "forecast"
            })
        
        self.chart_data = chart_points

    def set_selected_id(self, id_value: str):
        self.selected_id = id_value
        self.forecast_data = []
        self.current_forecast_version = 0
        self.load_production_data()

    def set_forecast_end_date(self, date: str):
        self.forecast_end_date = date

    def _get_next_forecast_version(self, session, unique_id: str) -> int:
        """Determine the next forecast version number using FIFO logic."""
        existing_versions = session.exec(
            select(InterventionForecast.Version, func.min(InterventionForecast.CreatedAt))
            .where(
                InterventionForecast.UniqueId == unique_id,
                InterventionForecast.Version > 0
            )
            .group_by(InterventionForecast.Version)
        ).all()
        
        if not existing_versions:
            return 1
        
        used_versions = [v[0] for v in existing_versions]
        
        if len(used_versions) < MAX_FORECAST_VERSIONS:
            for v in range(1, MAX_FORECAST_VERSIONS + 1):
                if v not in used_versions:
                    return v
        
        oldest_version = min(existing_versions, key=lambda x: x[1])[0]
        
        session.exec(
            delete(InterventionForecast).where(
                InterventionForecast.UniqueId == unique_id,
                InterventionForecast.Version == oldest_version
            )
        )
        session.commit()
        
        return oldest_version
    
    def _save_forecast_to_db(
        self, 
        unique_id: str, 
        forecast_points: list[ForecastPoint]
    ) -> int:
        """Save forecast data to InterventionForecast table with version control."""
        try:
            with rx.session() as session:
                version = self._get_next_forecast_version(session, unique_id)
                created_at = datetime.now()
                
                for fp in forecast_points:
                    prod_record = InterventionForecast(
                        UniqueId=unique_id,
                        Date=fp.date,
                        Version=version,
                        DataType="Forecast",
                        OilRate=fp.oil_rate,
                        LiqRate=fp.liq_rate,
                        Qoil=fp.q_oil,
                        Qliq=fp.q_liq,
                        WC=fp.wc,
                        CreatedAt=created_at
                    )
                    session.add(prod_record)
                
                session.commit()
                return version
                
        except Exception as e:
            print(f"Error saving forecast to DB: {e}")
            raise

    def run_forecast(self):
        """Run Arps decline curve forecast using pandas date_range and KMonth.
        
        For 'Plan' status: Uses PlanningDate as start with parameters from InterventionID
        For 'Done' status: Uses last production data as start point
        
        Uses K_int from KMonth table for intervention cumulative calculation:
        Qoil = K_int * days_in_month * OilRate
        """
        if not self.current_gtm or not self.forecast_end_date:
            return rx.toast.error("Please select an intervention and set forecast end date")
        
        try:
            # Arps decline parameters from current GTM
            qi_oil = self.current_gtm.InitialORate
            b_oil = self.current_gtm.bo
            di_oil = self.current_gtm.Dio
            
            qi_liq = self.current_gtm.InitialLRate
            b_liq = self.current_gtm.bl
            di_liq = self.current_gtm.Dil
            
            end_date = datetime.strptime(self.forecast_end_date, "%Y-%m-%d")
            
            # Determine start date based on status
            if self.current_gtm.Status == "Plan":
                start_date = datetime.strptime(self.current_gtm.PlanningDate, "%Y-%m-%d")
            else:
                if not self.history_prod:
                    return rx.toast.error("No production data available for forecasting")
                
                sorted_prod = sorted(self.history_prod, key=lambda x: x["Date"])
                last_prod = sorted_prod[-1]
                
                if isinstance(last_prod["Date"], datetime):
                    start_date = last_prod["Date"]
                else:
                    start_date = datetime.strptime(str(last_prod["Date"]), "%Y-%m-%d")
                
                # Use last actual rates as starting point
                qi_oil = last_prod["OilRate"] if last_prod["OilRate"] > 0 else qi_oil
                qi_liq = last_prod["LiqRate"] if last_prod["LiqRate"] > 0 else qi_liq
            
            # Move start date to next month start for forecasting
            start_date = (start_date.replace(day=1) + timedelta(days=32)).replace(day=1)
            
            if end_date <= start_date:
                return rx.toast.error(f"Forecast end date must be after {start_date.strftime('%Y-%m-%d')}")
            
            # Ensure KMonth data is loaded
            if not self.k_month_data:
                self.load_k_month_data()
            
            # Prepare K_int specific data for intervention
            k_int_data = {}
            for month_id, k_values in self.k_month_data.items():
                k_int_data[month_id] = {
                    "K_oil": k_values.get("K_int", 1.0),  # Use K_int for intervention
                    "K_liq": k_values.get("K_int", 1.0),
                    "K_int": k_values.get("K_int", 1.0)
                }
            
            # Run DCA forecast using utility function
            forecast_points = run_dca_forecast(
                start_date=start_date,
                end_date=end_date,
                qi_oil=qi_oil,
                di_oil=di_oil,
                b_oil=b_oil,
                qi_liq=qi_liq,
                di_liq=di_liq,
                b_liq=b_liq,
                k_month_data=k_int_data,
                use_exponential=self.use_exponential_dca
            )
            
            if not forecast_points:
                return rx.toast.error("No forecast points generated. Check date range.")
            
            # Save forecast to database with FIFO version control
            version = self._save_forecast_to_db(self.selected_id, forecast_points)
            
            # Update state
            self.forecast_data = [
                {
                    "date": fp.date.strftime("%Y-%m-%d"),
                    "oilRate": fp.oil_rate,
                    "liqRate": fp.liq_rate,
                    "qOil": fp.q_oil,
                    "qLiq": fp.q_liq,
                    "wc": fp.wc
                }
                for fp in forecast_points
            ]
            self.current_forecast_version = version
            
            # Reload available versions
            with rx.session() as session:
                forecast_versions = session.exec(
                    select(InterventionForecast.Version).where(
                        InterventionForecast.UniqueId == self.selected_id,
                        InterventionForecast.Version > 0
                    ).distinct()
                ).all()
                self.available_forecast_versions = sorted(forecast_versions)
            
            self.update_chart_data()
            
            # Calculate totals for message
            total_qoil = sum(fp.q_oil for fp in forecast_points)
            total_qliq = sum(fp.q_liq for fp in forecast_points)
            
            dca_type = "Exponential" if self.use_exponential_dca else "Hyperbolic"
            status_msg = "planned" if self.current_gtm.Status == "Plan" else "completed"
            
            return rx.toast.success(
                f"Forecast v{version} ({dca_type} DCA) for {status_msg} intervention: "
                f"{len(forecast_points)} months, Qoil={total_qoil:.0f}t, Qliq={total_qliq:.0f}t"
            )
            
        except Exception as e:
            print(f"Forecast error: {e}")
            import traceback
            traceback.print_exc()
            return rx.toast.error(f"Forecast failed: {str(e)}")

    def delete_forecast_version(self, version: int):
        """Delete a specific forecast version."""
        if version == 0:
            return rx.toast.error("Cannot delete base case forecast (version 0)")
        
        try:
            with rx.session() as session:
                session.exec(
                    delete(InterventionForecast).where(
                        InterventionForecast.UniqueId == self.selected_id,
                        InterventionForecast.Version == version
                    )
                )
                session.commit()
            
            self.load_production_data()
            return rx.toast.success(f"Forecast version {version} deleted")
            
        except Exception as e:
            print(f"Delete forecast error: {e}")
            return rx.toast.error(f"Failed to delete forecast: {str(e)}")

    async def handle_excel_upload(self, files: list[rx.UploadFile]):
        """Handle Excel file upload for interventions."""
        if not files:
            return rx.toast.error("No file selected")
        
        try:
            import pandas as pd
            
            file = files[0]
            upload_data = await file.read()
            
            import io
            df = pd.read_excel(io.BytesIO(upload_data))
            
            required_cols = [
                'UniqueId', 'Field', 'Platform', 'Reservoir', 'TypeGTM',
                'PlanningDate', 'Status', 'InitialORate', 'bo', 'Dio',
                'InitialLRate', 'bl', 'Dil'
            ]
            
            missing_cols = [c for c in required_cols if c not in df.columns]
            if missing_cols:
                return rx.toast.error(f"Missing columns: {', '.join(missing_cols)}")
            
            added_count = 0
            with rx.session() as session:
                for _, row in df.iterrows():
                    existing = session.exec(
                        select(Intervention).where(
                            Intervention.UniqueId == str(row['UniqueId'])
                        )
                    ).first()
                    
                    if not existing:
                        new_gtm = Intervention(
                            UniqueId=str(row['UniqueId']),
                            Field=str(row['Field']),
                            Platform=str(row['Platform']),
                            Reservoir=str(row['Reservoir']),
                            TypeGTM=str(row['TypeGTM']),
                            Category=str(row.get('Category', '')),
                            PlanningDate=str(row['PlanningDate'])[:10],
                            Status=str(row['Status']),
                            InitialORate=float(row['InitialORate']),
                            bo=float(row['bo']),
                            Dio=float(row['Dio']),
                            InitialLRate=float(row['InitialLRate']),
                            bl=float(row['bl']),
                            Dil=float(row['Dil']),
                            Describe=str(row.get('Describe', ''))
                        )
                        session.add(new_gtm)
                        added_count += 1
                
                session.commit()
            
            self.load_gtms()
            return rx.toast.success(f"Added {added_count} interventions from Excel")
            
        except Exception as e:
            print(f"Excel upload error: {e}")
            return rx.toast.error(f"Failed to load Excel: {str(e)}")

    def add_gtm(self, form_data: dict):
        """Add new GTM to database."""
        try:
            if not form_data.get("UniqueId"):
                return rx.toast.error("UniqueId is required!")
            
            if not form_data.get("PlanningDate"):
                return rx.toast.error("Planning Date is required!")
            
            form_data["InitialORate"] = float(form_data.get("InitialORate") or 0)
            form_data["bo"] = float(form_data.get("bo") or 0)
            form_data["Dio"] = float(form_data.get("Dio") or 0)
            form_data["InitialLRate"] = float(form_data.get("InitialLRate") or 0)
            form_data["bl"] = float(form_data.get("bl") or 0)
            form_data["Dil"] = float(form_data.get("Dil") or 0)
            
            if not form_data.get("Status"):
                form_data["Status"] = "Plan"
            if not form_data.get("Category"):
                form_data["Category"] = ""
            if not form_data.get("Describe"):
                form_data["Describe"] = ""
            
            with rx.session() as session:
                existing = session.exec(
                    select(Intervention).where(
                        Intervention.UniqueId == form_data["UniqueId"]
                    )
                ).first()
                
                if existing:
                    return rx.toast.error(f"UniqueId '{form_data['UniqueId']}' already exists!")
                
                new_gtm = Intervention(**form_data)
                session.add(new_gtm)
                session.commit()
                session.refresh(new_gtm)
            
            self.load_gtms()
            return rx.toast.success("GTM added successfully!")
            
        except Exception as e:
            print(f"Database error: {e}")
            return rx.toast.error(f"Failed to save GTM: {str(e)}")

    def get_gtm(self, gtm: Intervention):
        self.current_gtm = gtm

    def update_gtm(self, form_data: dict):
        """Update existing GTM in database with partial update support."""
        try:
            if not self.current_gtm:
                return rx.toast.error("No intervention selected for update")
            
            unique_id = self.current_gtm.UniqueId
            
            with rx.session() as session:
                gtm_to_update = session.exec(
                    select(Intervention).where(
                        Intervention.UniqueId == unique_id
                    )
                ).first()
                
                if not gtm_to_update:
                    return rx.toast.error(f"Intervention '{unique_id}' not found")
                
                string_fields = [
                    "Field", "Platform", "Reservoir", "TypeGTM", 
                    "Category", "PlanningDate", "Status", "Describe"
                ]
                for field in string_fields:
                    value = form_data.get(field)
                    if value is not None and str(value).strip():
                        setattr(gtm_to_update, field, str(value).strip())
                
                numeric_fields = [
                    ("InitialORate", "InitialORate"),
                    ("bo", "bo"),
                    ("Dio", "Dio"),
                    ("InitialLRate", "InitialLRate"),
                    ("bl", "bl"),
                    ("Dil", "Dil"),
                ]
                
                for form_key, model_field in numeric_fields:
                    value = form_data.get(form_key)
                    if value is not None and str(value).strip() != "":
                        try:
                            numeric_value = float(value)
                            setattr(gtm_to_update, model_field, numeric_value)
                        except (ValueError, TypeError) as e:
                            print(f"Warning: Could not convert {form_key}='{value}' to float: {e}")
                
                session.add(gtm_to_update)
                session.commit()
                session.refresh(gtm_to_update)
                self.current_gtm = gtm_to_update
            
            self.load_gtms()
            
            if self.selected_id == unique_id:
                self.intervention_date = self.current_gtm.PlanningDate
            
            return rx.toast.success(f"Intervention '{unique_id}' updated successfully!")
            
        except Exception as e:
            print(f"Update error: {e}")
            import traceback
            traceback.print_exc()
            return rx.toast.error(f"Failed to update GTM: {str(e)}")

    def delete_gtm(self, unique_id: str):
        """Delete GTM from database."""
        try:
            with rx.session() as session:
                gtm_to_delete = session.exec(
                    select(Intervention).where(
                        Intervention.UniqueId == unique_id
                    )
                ).first()
                
                if gtm_to_delete:
                    session.delete(gtm_to_delete)
                    session.commit()
                    
            self.load_gtms()
            return rx.toast.success("GTM deleted successfully!")
            
        except Exception as e:
            print(f"Delete error: {e}")
            return rx.toast.error(f"Failed to delete GTM: {str(e)}")

    def transform_data(self):
        """Transform GTM type data for visualization."""
        type_counts = Counter(gtm.TypeGTM for gtm in self.GTM)
        self.gtms_for_graph = [
            {"name": gtm_group, "value": count}
            for gtm_group, count in type_counts.items()
        ]
    
    @rx.var
    def total_interventions(self) -> int:
        return len(self.GTM)
    
    @rx.var
    def planned_interventions(self) -> int:
        return sum(1 for gtm in self.GTM if gtm.Status == "Plan")
    
    @rx.var
    def completed_interventions(self) -> int:
        return sum(1 for gtm in self.GTM if gtm.Status == "Done")
    
    @rx.var
    def production_table_data(self) -> list[dict]:
        """Get production data formatted for table display (last 24 records)."""
        sorted_data = sorted(
            self.history_prod, 
            key=lambda x: x["Date"], 
            reverse=True
        )[:24]
        
        return [
            {
                "Date": p["Date"].strftime("%Y-%m-%d") if isinstance(p["Date"], datetime) else str(p["Date"]),
                "OilRate": f"{p['OilRate']:.1f}",
                "LiqRate": f"{p['LiqRate']:.1f}",
                "WC": f"{p['WC']:.1f}"
            }
            for p in sorted_data
        ]
    
    @rx.var
    def forecast_table_data(self) -> list[dict]:
        """Get forecast data formatted for table display with cumulative production."""
        return [
            {
                "Date": f["date"],
                "OilRate": f"{f['oilRate']:.1f}",
                "LiqRate": f"{f['liqRate']:.1f}",
                "Qoil": f"{f.get('qOil', 0):.0f}",
                "Qliq": f"{f.get('qLiq', 0):.0f}"
            }
            for f in self.forecast_data[:12]  # Show first 12 months
        ]
    
    @rx.var
    def forecast_version_options(self) -> list[str]:
        return [f"v{v}" for v in self.available_forecast_versions]
    
    def set_forecast_version_from_str(self, version_str: str):
        if version_str and version_str.startswith("v"):
            version = int(version_str[1:])
            self.set_forecast_version(version)

    def delete_current_forecast_version(self):
        return self.delete_forecast_version(self.current_forecast_version)
    
    @rx.var
    def history_record_count(self) -> int:
        return len(self.history_prod)
    
    @rx.var
    def date_range_display(self) -> str:
        if not self.history_prod:
            return "No data"
        
        dates = [p["Date"] for p in self.history_prod]
        min_date = min(dates)
        max_date = max(dates)
        
        min_str = min_date.strftime("%Y-%m-%d") if isinstance(min_date, datetime) else str(min_date)
        max_str = max_date.strftime("%Y-%m-%d") if isinstance(max_date, datetime) else str(max_date)
        
        return f"{min_str} to {max_str}"
    
    @rx.var
    def forecast_totals_display(self) -> str:
        """Display total cumulative production from forecast."""
        if not self.forecast_data:
            return "No forecast"
        total_qoil = sum(f.get("qOil", 0) for f in self.forecast_data)
        total_qliq = sum(f.get("qLiq", 0) for f in self.forecast_data)
        return f"Total: Qoil={total_qoil:.0f}t | Qliq={total_qliq:.0f}t"
    
    @rx.var
    def k_month_loaded(self) -> bool:
        """Check if KMonth data is loaded."""
        return len(self.k_month_data) > 0