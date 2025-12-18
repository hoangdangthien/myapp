"""State management for Well Intervention (GTM) operations."""
import reflex as rx
from collections import Counter
from typing import Optional
from datetime import datetime, timedelta
import numpy as np
from sqlmodel import String, asc, cast, desc, func, or_, select, delete

from ..models import Intervention, InterventionForecast, HistoryProd, MAX_FORECAST_VERSIONS


class GTMState(rx.State):
    """State for managing Well Intervention (GTM) data.
    
    Handles CRUD operations, Excel import, forecasting with version control,
    and data transformations. Uses HistoryProd table for actual production data.
    """
    
    # List of all interventions
    GTM: list[Intervention] = []
    
    # Historical production data from HistoryProd table (last 5 years)
    history_prod: list[dict] = []
    
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
    
    # Phase selection for chart (checkboxes for multi-select)
    show_oil: bool = True
    show_liquid: bool = True
    show_wc: bool = True  # Water Cut toggle
    
    # Search/filter state
    search_value: str = ""
    selected_field: str = ""
    selected_status: str = ""
    
    # File upload state
    upload_progress: int = 0
    upload_status: str = ""
    
    # Dialog control state
    add_dialog_open: bool = False
    
    def set_add_dialog_open(self, is_open: bool):
        """Control add dialog open state."""
        self.add_dialog_open = is_open
    
    def toggle_oil(self, checked: bool):
        """Toggle oil phase visibility."""
        self.show_oil = checked
    
    def toggle_liquid(self, checked: bool):
        """Toggle liquid phase visibility."""
        self.show_liquid = checked
    
    def toggle_wc(self, checked: bool):
        """Toggle water cut visibility."""
        self.show_wc = checked

    def load_gtms(self):
        """Load all GTMs from database."""
        try:
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
        """Load production data for selected intervention from HistoryProd table.
        
        Fetches historical production data for the last 5 years and calculates
        Water Cut (WC) from Oilrate and Liqrate fields.
        
        WC Calculation: WC = (Liqrate - Oilrate) / Liqrate * 100
        """
        if not self.selected_id:
            self.history_prod = []
            self.chart_data = []
            return
            
        try:
            # Calculate date 5 years ago for filtering
            five_years_ago = datetime.now() - timedelta(days=5*365)
            
            with rx.session() as session:
                # Load historical production data from HistoryProd table (last 5 years)
                history_records = session.exec(
                    select(HistoryProd).where(
                        HistoryProd.UniqueId == self.selected_id,
                        HistoryProd.Date >= five_years_ago
                    ).order_by(desc(HistoryProd.Date))
                ).all()
                
                # Convert HistoryProd to internal format with calculated WC
                self.history_prod = []
                for rec in history_records:
                    # Calculate Water Cut: WC = (Liqrate - Oilrate) / Liqrate * 100
                    # This gives percentage of water in total liquid production
                    wc = 0.0
                    oil_rate = rec.OilRate if rec.OilRate else 0.0
                    liq_rate = rec.LiqRate if rec.LiqRate else 0.0
                    
                    if liq_rate > 0:
                        wc = ((liq_rate - oil_rate) / liq_rate) * 100
                        wc = max(0.0, min(100.0, wc))  # Clamp to 0-100%
                    
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
                
                # Load available forecast versions from InterventionForecast
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
            
            # Load latest forecast version if available
            if self.available_forecast_versions:
                self.current_forecast_version = max(self.available_forecast_versions)
                self.load_forecast_from_db()
            else:
                self.forecast_data = []
            
            # Transform to chart data
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
                    InterventionForecast.select().where(
                        InterventionForecast.UniqueId == self.selected_id,
                        InterventionForecast.Version == self.current_forecast_version
                    ).order_by(InterventionForecast.Date)
                ).all()
                
                self.forecast_data = [
                    {
                        "date": rec.Date.strftime("%Y-%m-%d") if isinstance(rec.Date, datetime) else str(rec.Date),
                        "oilRate": rec.OilRate,
                        "liqRate": rec.LiqRate
                    }
                    for rec in forecast_records
                ]
        except Exception as e:
            print(f"Error loading forecast from DB: {e}")
            self.forecast_data = []
    
    def set_forecast_version(self, version: int):
        """Set and load a specific forecast version."""
        self.current_forecast_version = version
        self.load_forecast_from_db()
        self.update_chart_data()
    
    def filter_intervention(self, search_value):
        self.search_value = search_value
        self.load_gtms()
    
    def update_chart_data(self):
        """Update chart data combining actual history and forecast with Water Cut."""
        chart_points = []
        
        # Add actual production data from HistoryProd (sorted by date ascending)
        sorted_history = sorted(self.history_prod, key=lambda x: x["Date"])
        for prod in sorted_history:
            date_val = prod["Date"]
            date_str = date_val.strftime("%Y-%m-%d") if isinstance(date_val, datetime) else str(date_val)
            chart_points.append({
                "date": date_str,
                "oilRate": prod["OilRate"],
                "liqRate": prod["LiqRate"],
                "wc": prod["WC"],  # Water Cut from history
                "type": "actual"
            })
        
        # Add forecast data if available
        for fc in self.forecast_data:
            # Calculate forecast WC from oil and liquid rates
            wc_forecast = 0.0
            if fc["liqRate"] > 0:
                wc_forecast = ((fc["liqRate"] - fc["oilRate"]) / fc["liqRate"]) * 100
                wc_forecast = max(0.0, min(100.0, wc_forecast))
            
            chart_points.append({
                "date": fc["date"],
                "oilRateForecast": fc["oilRate"],
                "liqRateForecast": fc["liqRate"],
                "wcForecast": round(wc_forecast, 2),  # Forecast Water Cut
                "type": "forecast"
            })
        
        self.chart_data = chart_points

    def set_selected_id(self, id_value: str):
        """Set selected intervention ID and load its data."""
        self.selected_id = id_value
        self.forecast_data = []
        self.current_forecast_version = 0
        self.load_production_data()

    def set_forecast_end_date(self, date: str):
        """Set the forecast end date."""
        self.forecast_end_date = date

    def _get_next_forecast_version(self, session, unique_id: str) -> int:
        """Determine the next forecast version number using FIFO logic.
        
        Returns the version number to use (1, 2, or 3).
        If all 3 versions exist, removes the oldest and returns its version number.
        """
        # Get existing forecast versions with their creation timestamps
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
        
        # If less than MAX_FORECAST_VERSIONS, find next available
        if len(used_versions) < MAX_FORECAST_VERSIONS:
            for v in range(1, MAX_FORECAST_VERSIONS + 1):
                if v not in used_versions:
                    return v
        
        # All versions used - find oldest by CreatedAt and remove it (FIFO)
        oldest_version = min(existing_versions, key=lambda x: x[1])[0]
        
        # Delete oldest version's records
        session.exec(
            delete(InterventionForecast).where(
                InterventionForecast.UniqueId == unique_id,
                InterventionForecast.Version == oldest_version
            )
        )
        session.commit()
        
        return oldest_version
    
    def _save_forecast_to_db(self, unique_id: str, forecast_points: list[dict]) -> int:
        """Save forecast data to InterventionForecast table with version control.
        
        Args:
            unique_id: The well/intervention identifier
            forecast_points: List of forecast data points with date, oilRate, liqRate
            
        Returns:
            The version number used for this forecast
        """
        try:
            with rx.session() as session:
                # Determine next version using FIFO
                version = self._get_next_forecast_version(session, unique_id)
                
                # Calculate cumulative production
                cum_oil = 0.0
                cum_liq = 0.0
                prev_date = None
                
                created_at = datetime.now()
                
                for point in forecast_points:
                    date = datetime.strptime(point["date"], "%Y-%m-%d")
                    oil_rate = point["oilRate"]
                    liq_rate = point["liqRate"]
                    
                    # Calculate cumulative (simple monthly integration)
                    if prev_date:
                        days = (date - prev_date).days
                        cum_oil += oil_rate * days
                        cum_liq += liq_rate * days
                    
                    # Calculate water cut
                    wc = ((liq_rate - oil_rate) / liq_rate * 100) if liq_rate > 0 else 0
                    
                    # Create record
                    prod_record = InterventionForecast(
                        UniqueId=unique_id,
                        Date=date,
                        Version=version,
                        DataType="Forecast",
                        OilRate=oil_rate,
                        OilProd=cum_oil,
                        LiqRate=liq_rate,
                        LiqProd=cum_liq,
                        WC=max(0, min(100, wc)),  # Clamp to 0-100%
                        CreatedAt=created_at
                    )
                    session.add(prod_record)
                    prev_date = date
                
                session.commit()
                return version
                
        except Exception as e:
            print(f"Error saving forecast to DB: {e}")
            raise

    def run_forecast(self):
        """Run Arps decline curve forecast for selected intervention.
        
        For 'Plan' status: Uses PlanningDate as start date with parameters from InterventionID
        For 'Done' status: Uses last production data as start point
        
        After generating forecast, saves to InterventionForecast table with version control (FIFO, max 3).
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
            
            # Determine start date and initial rates based on status
            if self.current_gtm.Status == "Plan":
                # For planned interventions: start from PlanningDate with design parameters
                start_date = datetime.strptime(self.current_gtm.PlanningDate, "%Y-%m-%d")
                
            else:
                # For completed interventions: use last production data if available
                if not self.history_prod:
                    return rx.toast.error("No production data available for forecasting")
                
                # Sort by date and get latest record
                sorted_prod = sorted(self.history_prod, key=lambda x: x["Date"])
                last_prod = sorted_prod[-1]
                
                # Handle Date field (could be datetime or string)
                if isinstance(last_prod["Date"], datetime):
                    start_date = last_prod["Date"]
                else:
                    start_date = datetime.strptime(str(last_prod["Date"]), "%Y-%m-%d")
                
                # Use last actual rates as starting point
                qi_oil = last_prod["OilRate"] if last_prod["OilRate"] > 0 else qi_oil
                qi_liq = last_prod["LiqRate"] if last_prod["LiqRate"] > 0 else qi_liq
            
            if end_date <= start_date:
                return rx.toast.error(f"Forecast end date must be after {start_date.strftime('%Y-%m-%d')}")
            
            # Generate forecast
            forecast_points = []
            current_date = start_date + timedelta(days=30)  # Monthly forecast
            t = 1  # Time in months
            
            while current_date <= end_date:
                # Arps hyperbolic decline: q(t) = qi / (1 + b*Di*t)^(1/b)
                if b_oil > 0 and di_oil > 0:
                    oil_rate = qi_oil / ((1 + b_oil * di_oil * t) ** (1/b_oil))
                else:
                    oil_rate = qi_oil * np.exp(-di_oil * t) if di_oil > 0 else qi_oil
                
                if b_liq > 0 and di_liq > 0:
                    liq_rate = qi_liq / ((1 + b_liq * di_liq * t) ** (1/b_liq))
                else:
                    liq_rate = qi_liq * np.exp(-di_liq * t) if di_liq > 0 else qi_liq
                
                forecast_points.append({
                    "date": current_date.strftime("%Y-%m-%d"),
                    "oilRate": max(0, round(oil_rate, 2)),
                    "liqRate": max(0, round(liq_rate, 2))
                })
                
                current_date += timedelta(days=30)
                t += 1
            
            if not forecast_points:
                return rx.toast.error("No forecast points generated. Check date range.")
            
            # Save forecast to database with FIFO version control
            version = self._save_forecast_to_db(self.selected_id, forecast_points)
            
            # Update state
            self.forecast_data = forecast_points
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
            
            status_msg = "planned intervention" if self.current_gtm.Status == "Plan" else "completed intervention"
            return rx.toast.success(
                f"Forecast v{version} saved for {status_msg} with {len(forecast_points)} points"
            )
            
        except Exception as e:
            print(f"Forecast error: {e}")
            return rx.toast.error(f"Forecast failed: {str(e)}")

    def delete_forecast_version(self, version: int):
        """Delete a specific forecast version."""
        if version == 0:
            return rx.toast.error("Cannot delete actual production data")
        
        try:
            with rx.session() as session:
                session.exec(
                    delete(InterventionForecast).where(
                        InterventionForecast.UniqueId == self.selected_id,
                        InterventionForecast.Version == version
                    )
                )
                session.commit()
            
            # Reload data
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
            
            # Read Excel file
            import io
            df = pd.read_excel(io.BytesIO(upload_data))
            
            # Required columns
            required_cols = [
                'UniqueId', 'Field', 'Platform', 'Reservoir', 'TypeGTM',
                'PlanningDate', 'Status', 'InitialORate', 'bo', 'Dio',
                'InitialLRate', 'bl', 'Dil'
            ]
            
            # Check for required columns
            missing_cols = [c for c in required_cols if c not in df.columns]
            if missing_cols:
                return rx.toast.error(f"Missing columns: {', '.join(missing_cols)}")
            
            # Insert records
            added_count = 0
            with rx.session() as session:
                for _, row in df.iterrows():
                    # Check if exists
                    existing = session.exec(
                        Intervention.select().where(
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
                            PlanningDate=str(row['PlanningDate'])[:10],
                            Status=str(row['Status']),
                            InitialORate=float(row['InitialORate']),
                            bo=float(row['bo']),
                            Dio=float(row['Dio']),
                            InitialLRate=float(row['InitialLRate']),
                            bl=float(row['bl']),
                            Dil=float(row['Dil'])
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
        """Add new GTM to database using Reflex/SQLModel."""
        try:
            # Ensure all required fields have values
            if not form_data.get("UniqueId"):
                return rx.toast.error("UniqueId is required!")
            
            if not form_data.get("PlanningDate"):
                return rx.toast.error("Planning Date is required!")
            
            # Convert numeric fields with defaults
            form_data["InitialORate"] = float(form_data.get("InitialORate") or 0)
            form_data["bo"] = float(form_data.get("bo") or 0)
            form_data["Dio"] = float(form_data.get("Dio") or 0)
            form_data["InitialLRate"] = float(form_data.get("InitialLRate") or 0)
            form_data["bl"] = float(form_data.get("bl") or 0)
            form_data["Dil"] = float(form_data.get("Dil") or 0)
            
            # Set default status if not provided
            if not form_data.get("Status"):
                form_data["Status"] = "Plan"
            
            with rx.session() as session:
                existing = session.exec(
                    Intervention.select().where(
                        Intervention.UniqueId == form_data["UniqueId"]
                    )
                ).first()
                
                if existing:
                    return rx.toast.error(
                        f"UniqueId '{form_data['UniqueId']}' already exists!"
                    )
                
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
        """Set the current GTM for editing."""
        self.current_gtm = gtm

    def update_gtm(self, form_data: dict):
        """Update existing GTM in database with partial update support.
        
        After updating, refreshes current_gtm to ensure forecast uses latest values.
        """
        try:
            with rx.session() as session:
                gtm_to_update = session.exec(
                    Intervention.select().where(
                        Intervention.UniqueId == self.current_gtm.UniqueId
                    )
                ).first()
                
                if gtm_to_update:
                    # Update string fields only if non-empty value provided
                    string_fields = ["Field", "Platform", "Reservoir", "TypeGTM", "PlanningDate", "Status"]
                    for field in string_fields:
                        value = form_data.get(field)
                        if value and str(value).strip():
                            setattr(gtm_to_update, field, value)
                    
                    # Update numeric fields
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
                        if value is not None and value != "":
                            try:
                                numeric_value = float(value)
                                setattr(gtm_to_update, model_field, numeric_value)
                            except (ValueError, TypeError):
                                pass
                    
                    session.add(gtm_to_update)
                    session.commit()
                    
                    # Refresh the session to get updated data
                    session.refresh(gtm_to_update)
                    
                    # Update current_gtm with fresh data so forecast uses new values
                    self.current_gtm = gtm_to_update
                    
            # Reload GTM list to reflect changes in table
            self.load_gtms()
            
            # If this is the selected intervention, also update intervention_date
            if self.selected_id == self.current_gtm.UniqueId:
                self.intervention_date = self.current_gtm.PlanningDate
            
            return rx.toast.success("GTM updated successfully!")
            
        except Exception as e:
            print(f"Update error: {e}")
            return rx.toast.error(f"Failed to update GTM: {str(e)}")

    def delete_gtm(self, unique_id: str):
        """Delete GTM from database."""
        try:
            with rx.session() as session:
                gtm_to_delete = session.exec(
                    Intervention.select().where(
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
        """Get total count of interventions."""
        return len(self.GTM)
    
    @rx.var
    def planned_interventions(self) -> int:
        """Get count of planned interventions."""
        return sum(1 for gtm in self.GTM if gtm.Status == "Plan")
    
    @rx.var
    def completed_interventions(self) -> int:
        """Get count of completed interventions."""
        return sum(1 for gtm in self.GTM if gtm.Status == "Done")
    
    @rx.var
    def production_table_data(self) -> list[dict]:
        """Get production data formatted for table display (last 24 records).
        
        Data sourced from HistoryProd table with calculated WC.
        Shows last 24 records, or all records if fewer than 24 available.
        """
        # Sort by date descending and take up to 24 records
        sorted_data = sorted(
            self.history_prod, 
            key=lambda x: x["Date"], 
            reverse=True
        )[:24]  # Take last 24 records (or all if less than 24)
        
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
        """Get forecast data formatted for table display."""
        return [
            {
                "Date": f["date"],
                "OilRate": f"{f['oilRate']:.1f}",
                "LiqRate": f"{f['liqRate']:.1f}"
            }
            for f in self.forecast_data[:10]
        ]
    
    @rx.var
    def forecast_version_options(self) -> list[str]:
        """Get available forecast versions as string options for dropdown."""
        return [f"v{v}" for v in self.available_forecast_versions]
    
    def set_forecast_version_from_str(self, version_str: str):
        """Convert 'v1' -> 1 in backend."""
        if version_str and version_str.startswith("v"):
            version = int(version_str[1:])
            self.set_forecast_version(version)

    def delete_current_forecast_version(self):
        """Wrapper to delete current version without frontend lambda."""
        return self.delete_forecast_version(self.current_forecast_version)
    
    @rx.var
    def history_record_count(self) -> int:
        """Get count of history production records loaded."""
        return len(self.history_prod)
    
    @rx.var
    def date_range_display(self) -> str:
        """Get date range of loaded history data."""
        if not self.history_prod:
            return "No data"
        
        dates = [p["Date"] for p in self.history_prod]
        min_date = min(dates)
        max_date = max(dates)
        
        min_str = min_date.strftime("%Y-%m-%d") if isinstance(min_date, datetime) else str(min_date)
        max_str = max_date.strftime("%Y-%m-%d") if isinstance(max_date, datetime) else str(max_date)
        
        return f"{min_str} to {max_str}"