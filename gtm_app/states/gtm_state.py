"""Refactored GTM State using DCA Service and Shared State.

This state manages Well Intervention (GTM) operations with improved
code organization using service classes.

DCA Formula: q(t) = qi * exp(-di * 12/365 * t)
For interventions: Qoil = OilRate * K_int * days_in_month

Base Forecast (Version 0): Production decline WITHOUT intervention
"""
import reflex as rx
from collections import Counter
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timedelta
import pandas as pd
import io
from sqlmodel import select, delete, func, or_
import plotly.graph_objects as go

from ..models import (
    Intervention,
    InterventionForecast,
    HistoryProd,
    MAX_FORECAST_VERSIONS
)
from ..services.dca_service import DCAService, ForecastConfig, ForecastResult
from ..services.database_service import DatabaseService
from .shared_state import SharedForecastState


# Validation ranges for numeric fields
VALIDATION_RULES = {
    "InitialORate": {"min": 0, "max": 10000, "name": "Initial Oil Rate", "unit": "t/day"},
    "InitialLRate": {"min": 0, "max": 20000, "name": "Initial Liquid Rate", "unit": "t/day"},
    "bo": {"min": 0, "max": 2, "name": "b (oil)", "unit": ""},
    "bl": {"min": 0, "max": 2, "name": "b (liquid)", "unit": ""},
    "Dio": {"min": 0, "max": 1, "name": "Di (oil)", "unit": "1/year"},
    "Dil": {"min": 0, "max": 1, "name": "Di (liquid)", "unit": "1/year"},
}


class GTMState(SharedForecastState):
    """State for managing Well Intervention (GTM) data.
    
    Inherits common functionality from SharedForecastState.
    """
    
    # List of all interventions
    GTM: List[Intervention] = []
    
    # Data for graph visualization
    gtms_for_graph: List[dict] = []
    
    # Currently selected intervention
    current_gtm: Optional[Intervention] = None
    selected_id: str = ""
    available_ids: List[str] = []
    
    # Base forecast data (version 0 - without intervention)
    base_forecast_data: List[dict] = []
    has_base_forecast: bool = False
    
    
    # Intervention date for vertical line
    intervention_date: str = ""
    
    # Search/filter state
    search_value: str = ""
    selected_field: str = ""
    selected_status: str = ""
    
    # File upload state
    upload_progress: int = 0
    upload_status: str = ""
    
    # Dialog control
    add_dialog_open: bool = False
    
    # ========== Summary Tables State ==========
    current_year_summary: List[dict] = []
    next_year_summary: List[dict] = []
    current_year: int = datetime.now().year
    next_year: int = datetime.now().year + 1

    @staticmethod
    def _validate_numeric_ranges(form_data: dict) -> Tuple[bool, str]:
        """Validate numeric fields are within allowed ranges.
        
        Args:
            form_data: Form data dictionary
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        errors = []
        
        for field, rules in VALIDATION_RULES.items():
            value = form_data.get(field)
            if value is not None and str(value).strip() != "":
                try:
                    num_value = float(value)
                    min_val = rules["min"]
                    max_val = rules["max"]
                    
                    if num_value < min_val:
                        errors.append(f"{rules['name']}: must be ≥ {min_val} (got {num_value})")
                    elif num_value > max_val:
                        errors.append(f"{rules['name']}: must be ≤ {max_val} (got {num_value})")
                except (ValueError, TypeError):
                    errors.append(f"{rules['name']}: invalid number '{value}'")
        
        if errors:
            return False, "; ".join(errors[:3])  # Return first 3 errors
        return True, ""

    @staticmethod
    def _validate_excel_row(row: pd.Series, row_index: int) -> Tuple[bool, str]:
        """Validate a row from Excel upload.
        
        Args:
            row: Pandas Series representing a row
            row_index: Row number for error messages
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        errors = []
        
        for field, rules in VALIDATION_RULES.items():
            if field in row:
                value = row[field]
                if pd.notna(value):
                    try:
                        num_value = float(value)
                        min_val = rules["min"]
                        max_val = rules["max"]
                        
                        if num_value < min_val or num_value > max_val:
                            errors.append(f"Row {row_index}: {field}={num_value} out of range [{min_val}, {max_val}]")
                    except (ValueError, TypeError):
                        errors.append(f"Row {row_index}: {field} invalid number")
        
        if errors:
            return False, "; ".join(errors)
        return True, ""

    

    def set_add_dialog_open(self, is_open: bool):
        self.add_dialog_open = is_open

    def load_gtms(self):
        """Load all GTMs from database."""
        try:
            self._load_k_month_data()
            
            with rx.session() as session:
                query = select(Intervention)
                if self.search_value:
                    search_value = f"%{str(self.search_value).lower()}%"
                    query = query.where(
                        or_(
                            Intervention.UniqueId.ilike(search_value),
                            Intervention.Field.ilike(search_value),
                            Intervention.Platform.ilike(search_value)
                        )
                    )
                self.GTM = session.exec(query).all()
            
            self.transform_data()
            self.available_ids = [gtm.UniqueId for gtm in self.GTM]
            
            if self.available_ids and not self.selected_id:
                self.selected_id = self.available_ids[0]
                self.load_production_data()
            
            self.load_forecast_summary_tables()
            
        except Exception as e:
            print(f"Error loading GTMs: {e}")
            self.GTM = []

    def load_production_data(self):
        """Load production data for selected intervention."""
        if not self.selected_id:
            self.history_prod = []
            self.chart_data = []
            self.base_forecast_data = []
            self.has_base_forecast = False
            return
            
        try:
            with rx.session() as session:
                self.history_prod = DCAService.load_history_data(session, self.selected_id, years=5)
                
                self.available_forecast_versions = DatabaseService.get_available_versions(
                    session, InterventionForecast, self.selected_id, min_version=1
                )
                
                self.has_base_forecast = DatabaseService.check_record_exists(
                    session, InterventionForecast,
                    {"UniqueId": self.selected_id, "Version": 0}
                )
            
            selected_gtm = next(
                (g for g in self.GTM if g.UniqueId == self.selected_id), None
            )
            if selected_gtm:
                self.intervention_date = selected_gtm.PlanningDate.split(" ")[0] 
                self.current_gtm = selected_gtm
            
            self.load_base_forecast_from_db()
            
            if self.available_forecast_versions:
                self.current_forecast_version = max(self.available_forecast_versions)
                self.load_forecast_from_db()
            else:
                self.forecast_data = []
            
            self._update_chart_with_base()
            
        except Exception as e:
            print(f"Error loading production data: {e}")
            self.history_prod = []

    def load_base_forecast_from_db(self):
        """Load base forecast (version 0) from database."""
        if not self.selected_id:
            self.base_forecast_data = []
            self.has_base_forecast = False
            return
            
        try:
            with rx.session() as session:
                self.base_forecast_data = DatabaseService.load_forecast_by_version(
                    session, InterventionForecast, self.selected_id, version=0
                )
                self.has_base_forecast = len(self.base_forecast_data) > 0
        except Exception as e:
            print(f"Error loading base forecast: {e}")
            self.base_forecast_data = []
            self.has_base_forecast = False

    def load_forecast_from_db(self):
        """Load forecast data for current version from database."""
        if not self.selected_id or self.current_forecast_version == 0:
            self.forecast_data = []
            return
        
        try:
            with rx.session() as session:
                self.forecast_data = DatabaseService.load_forecast_by_version(
                    session, InterventionForecast, self.selected_id, self.current_forecast_version
                )
        except Exception as e:
            print(f"Error loading forecast: {e}")
            self.forecast_data = []

    def _update_chart_with_base(self):
        """Update chart data including base forecast."""
        self.chart_data = DCAService.build_chart_data(
            history_prod=self.history_prod,
            forecast_data=self.forecast_data,
            base_forecast_data=self.base_forecast_data
        )

    def set_forecast_version(self, version: int):
        """Set and load a specific forecast version."""
        self.current_forecast_version = version
        self.load_forecast_from_db()
        self._update_chart_with_base()

    def set_forecast_version_from_str(self, version_str: str):
        """Set forecast version from string."""
        if version_str and version_str.startswith("v"):
            version = int(version_str[1:])
            self.set_forecast_version(version)

    def filter_intervention(self, search_value):
        """Filter interventions by search value."""
        self.search_value = search_value
        self.load_gtms()

    def set_selected_id(self, id_value: str):
        """Set selected intervention ID."""
        self.selected_id = id_value
        self.forecast_data = []
        self.base_forecast_data = []
        self.current_forecast_version = 0
        self.has_base_forecast = False
        self.load_production_data()

    def generate_base_forecast(self):
        """Generate base forecast (version 0) - production decline WITHOUT intervention."""
        if not self.history_prod:
            return rx.toast.error("No production history available")
        
        if not self.forecast_end_date:
            return rx.toast.error("Please set forecast end date first")
        
        try:
            sorted_prod = sorted(self.history_prod, key=lambda x: x["Date"])
            last_prod = sorted_prod[-1]
            
            if isinstance(last_prod["Date"], datetime):
                start_date = last_prod["Date"]
            else:
                start_date = datetime.strptime(str(last_prod["Date"]), "%Y-%m-%d")
            
            end_date = datetime.strptime(self.forecast_end_date, "%Y-%m-%d")
            
            if end_date <= start_date:
                return rx.toast.error(f"End date must be after {start_date.strftime('%Y-%m-%d')}")
            
            # Use lower decline rate for base case
            di_oil = self.current_gtm.Dio * 0.5 if self.current_gtm and self.current_gtm.Dio else 0.1
            
            config = ForecastConfig(
                qi_oil=last_prod["OilRate"],
                di_oil=di_oil,
                b_oil=0.0,
                qi_liq=last_prod["LiqRate"],
                di_liq=di_oil,
                b_liq=0.0,
                start_date=start_date,
                end_date=end_date,
                use_exponential=True,
                k_month_data=self.k_month_data
            )
            
            result = DCAService.run_intervention_forecast(config)
            
            if not result.is_success:
                return rx.toast.error(result.error or "Base forecast failed")
            
            # Save as version 0
            with rx.session() as session:
                DCAService.save_forecast(
                    session, InterventionForecast, self.selected_id,
                    result.forecast_points, version=0, data_type="Forecast"
                )
            
            self.base_forecast_data = DCAService.forecast_to_dict_list(result.forecast_points)
            self.has_base_forecast = True
            self._update_chart_with_base()
            
            return rx.toast.success(
                f"Base forecast (v0): {result.months} months, Qoil={result.total_qoil:.0f}t"
            )
            
        except Exception as e:
            print(f"Base forecast error: {e}")
            return rx.toast.error(f"Base forecast failed: {str(e)}")

    def run_forecast(self):
        """Run Arps decline curve forecast for intervention."""
        if not self.current_gtm or not self.forecast_end_date:
            return rx.toast.error("Please select an intervention and set forecast end date")
        
        try:
            qi_oil = self.current_gtm.InitialORate
            b_oil = self.current_gtm.bo
            di_oil = self.current_gtm.Dio
            qi_liq = self.current_gtm.InitialLRate
            b_liq = self.current_gtm.bl
            di_liq = self.current_gtm.Dil
            
            end_date = datetime.strptime(self.forecast_end_date, "%Y-%m-%d")
            
            if self.current_gtm.Status == "Plan":
                start_date = datetime.strptime(self.current_gtm.PlanningDate, "%Y-%m-%d")
            else:
                if not self.history_prod:
                    return rx.toast.error("No production data available")
                
                sorted_prod = sorted(self.history_prod, key=lambda x: x["Date"])
                last_prod = sorted_prod[-1]
                
                if isinstance(last_prod["Date"], datetime):
                    start_date = last_prod["Date"]
                else:
                    start_date = datetime.strptime(str(last_prod["Date"]), "%Y-%m-%d")
                
                qi_oil = last_prod["OilRate"] if last_prod["OilRate"] > 0 else qi_oil
                qi_liq = last_prod["LiqRate"] if last_prod["LiqRate"] > 0 else qi_liq
            
            if end_date <= start_date:
                return rx.toast.error(f"End date must be after {start_date.strftime('%Y-%m-%d')}")
            
            self._load_k_month_data()
            
            config = ForecastConfig(
                qi_oil=qi_oil,
                di_oil=di_oil,
                b_oil=b_oil,
                qi_liq=qi_liq,
                di_liq=di_liq,
                b_liq=b_liq,
                start_date=start_date,
                end_date=end_date,
                use_exponential=self.use_exponential_dca,
                k_month_data=self.k_month_data
            )
            
            result = DCAService.run_intervention_forecast(config)
            
            if not result.is_success:
                return rx.toast.error(result.error or "Forecast failed")
            
            # Save forecast
            with rx.session() as session:
                version = DCAService.get_next_version_fifo(
                    session, InterventionForecast, self.selected_id,
                    MAX_FORECAST_VERSIONS, min_version=1
                )
                DCAService.save_forecast(
                    session, InterventionForecast, self.selected_id,
                    result.forecast_points, version, data_type="Forecast"
                )
            
            self.forecast_data = DCAService.forecast_to_dict_list(result.forecast_points)
            self.current_forecast_version = version
            
            with rx.session() as session:
                self.available_forecast_versions = DatabaseService.get_available_versions(
                    session, InterventionForecast, self.selected_id, min_version=1
                )
            
            if not self.has_base_forecast:
                self.generate_base_forecast()
            
            self._update_chart_with_base()
            self.load_forecast_summary_tables()
            
            dca_type = "Exponential" if self.use_exponential_dca else "Hyperbolic"
            return rx.toast.success(
                f"Forecast v{version} ({dca_type}): {result.months} months, Qoil={result.total_qoil:.0f}t"
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
            self.load_forecast_summary_tables()
            return rx.toast.success(f"Forecast version {version} deleted")
            
        except Exception as e:
            return rx.toast.error(f"Failed to delete forecast: {str(e)}")

    def delete_current_forecast_version(self):
        """Delete the current forecast version."""
        return self.delete_forecast_version(self.current_forecast_version)

    def delete_base_forecast(self):
        """Delete base forecast (version 0)."""
        try:
            with rx.session() as session:
                session.exec(
                    delete(InterventionForecast).where(
                        InterventionForecast.UniqueId == self.selected_id,
                        InterventionForecast.Version == 0
                    )
                )
                session.commit()
            
            self.base_forecast_data = []
            self.has_base_forecast = False
            self._update_chart_with_base()
            
            return rx.toast.success("Base forecast (v0) deleted")
            
        except Exception as e:
            return rx.toast.error(f"Failed to delete base forecast: {str(e)}")

    def load_forecast_summary_tables(self):
        """Load forecast summary data for current year and next year."""
        try:
            current_year = datetime.now().year
            next_year = current_year + 1
            
            self.current_year = current_year
            self.next_year = next_year
            
            with rx.session() as session:
                interventions = session.exec(select(Intervention)).all()
                
                intervention_dict = {
                    gtm.UniqueId: {
                        "Field": gtm.Field,
                        "Platform": gtm.Platform,
                        "Reservoir": gtm.Reservoir,
                        "Type": gtm.TypeGTM,
                        "Category": gtm.Category,
                        "Status": gtm.Status,
                        "Date": gtm.PlanningDate
                    }
                    for gtm in interventions
                }
                
                forecast_records = session.exec(
                    select(InterventionForecast).where(InterventionForecast.Version > 0)
                ).all()
                
                # Group by UniqueId and Version
                forecast_by_uid: Dict[str, Dict[int, List]] = {}
                for rec in forecast_records:
                    uid = rec.UniqueId
                    ver = rec.Version
                    if uid not in forecast_by_uid:
                        forecast_by_uid[uid] = {}
                    if ver not in forecast_by_uid[uid]:
                        forecast_by_uid[uid][ver] = []
                    forecast_by_uid[uid][ver].append(rec)
                
                current_year_data = []
                next_year_data = []
                
                for uid, versions in forecast_by_uid.items():
                    if uid not in intervention_dict:
                        continue
                    
                    latest_version = max(versions.keys())
                    records = versions[latest_version]
                    details = intervention_dict[uid]
                    
                    current_year_monthly = {m: 0.0 for m in range(1, 13)}
                    next_year_monthly = {m: 0.0 for m in range(1, 13)}
                    
                    for rec in records:
                        rec_date = rec.Date if isinstance(rec.Date, datetime) else datetime.strptime(str(rec.Date), "%Y-%m-%d")
                        rec_year = rec_date.year
                        rec_month = rec_date.month
                        qoil = rec.Qoil if rec.Qoil else 0.0
                        
                        if rec_year == current_year:
                            current_year_monthly[rec_month] += qoil
                        elif rec_year == next_year:
                            next_year_monthly[rec_month] += qoil
                    
                    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
                    
                    base_row = {
                        "UniqueId": uid,
                        "Field": details["Field"],
                        "Platform": details["Platform"],
                        "Reservoir": details["Reservoir"],
                        "Type": details["Type"],
                        "Category": details["Category"],
                        "Status": details["Status"],
                        "Date": details["Date"],
                    }
                    
                    current_year_row = base_row.copy()
                    next_year_row = base_row.copy()
                    
                    for i, name in enumerate(month_names, 1):
                        current_year_row[name] = round(current_year_monthly[i], 1)
                        next_year_row[name] = round(next_year_monthly[i], 1)
                    
                    current_year_row["Total"] = round(sum(current_year_monthly.values()), 1)
                    next_year_row["Total"] = round(sum(next_year_monthly.values()), 1)
                    
                    if sum(current_year_monthly.values()) > 0:
                        current_year_data.append(current_year_row)
                    if sum(next_year_monthly.values()) > 0:
                        next_year_data.append(next_year_row)
                
                self.current_year_summary = sorted(current_year_data, key=lambda x: x["UniqueId"])
                self.next_year_summary = sorted(next_year_data, key=lambda x: x["UniqueId"])
                
        except Exception as e:
            print(f"Error loading forecast summary: {e}")
            self.current_year_summary = []
            self.next_year_summary = []

    def download_current_year_excel(self):
        """Download current year summary as Excel file."""
        return self._download_summary_excel(self.current_year_summary, self.current_year)

    def download_next_year_excel(self):
        """Download next year summary as Excel file."""
        return self._download_summary_excel(self.next_year_summary, self.next_year)

    def _download_summary_excel(self, data: List[dict], year: int):
        """Download summary data as Excel file."""
        if not data:
            return rx.toast.error(f"No data available for {year}")
        
        try:
            df = pd.DataFrame(data)
            columns_order = [
                "UniqueId", "Field", "Platform", "Reservoir", "Type", "Category",
                "Status", "Date", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Total"
            ]
            df = df[columns_order]
            
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name=f'Qoil_Forecast_{year}', index=False)
            
            output.seek(0)
            return rx.download(
                data=output.getvalue(),
                filename=f"Intervention_Qoil_Forecast_{year}.xlsx",
            )
            
        except Exception as e:
            return rx.toast.error(f"Failed to download Excel: {str(e)}")

    def download_both_years_excel(self):
        """Download both years summary as single Excel file."""
        if not self.current_year_summary and not self.next_year_summary:
            return rx.toast.error("No forecast data available")
        
        try:
            columns_order = [
                "UniqueId", "Field", "Platform", "Reservoir", "Type", "Category",
                "Status", "Date", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Total"
            ]
            
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                if self.current_year_summary:
                    df_current = pd.DataFrame(self.current_year_summary)[columns_order]
                    df_current.to_excel(writer, sheet_name=f'Qoil_{self.current_year}', index=False)
                
                if self.next_year_summary:
                    df_next = pd.DataFrame(self.next_year_summary)[columns_order]
                    df_next.to_excel(writer, sheet_name=f'Qoil_{self.next_year}', index=False)
            
            output.seek(0)
            return rx.download(
                data=output.getvalue(),
                filename=f"Intervention_Qoil_Forecast_{self.current_year}_{self.next_year}.xlsx",
            )
            
        except Exception as e:
            return rx.toast.error(f"Failed to download Excel: {str(e)}")

    async def handle_excel_upload(self, files: List[rx.UploadFile]):
        """Handle Excel file upload for interventions with validation."""
        if not files:
            return rx.toast.error("No file selected")
        
        try:
            file = files[0]
            upload_data = await file.read()
            df = pd.read_excel(io.BytesIO(upload_data))
            
            required_cols = [
                'UniqueId', 'Field', 'Platform', 'Reservoir', 'TypeGTM',
                'PlanningDate', 'Status', 'InitialORate', 'bo', 'Dio',
                'InitialLRate', 'bl', 'Dil'
            ]
            
            missing_cols = [c for c in required_cols if c not in df.columns]
            if missing_cols:
                return rx.toast.error(f"Missing columns: {', '.join(missing_cols)}")
            
            # Validate all rows first
            validation_errors = []
            for idx, row in df.iterrows():
                is_valid, error_msg = self._validate_excel_row(row, idx + 2)  # +2 for Excel row number
                if not is_valid:
                    validation_errors.append(error_msg)
            
            if validation_errors:
                error_summary = "; ".join(validation_errors[:5])  # Show first 5 errors
                if len(validation_errors) > 5:
                    error_summary += f" ... and {len(validation_errors) - 5} more errors"
                return rx.toast.error(f"Validation failed: {error_summary}")
            
            added_count = 0
            skipped_count = 0
            
            with rx.session() as session:
                for _, row in df.iterrows():
                    existing = session.exec(
                        select(Intervention).where(Intervention.UniqueId == str(row['UniqueId']))
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
                    else:
                        skipped_count += 1
                
                session.commit()
            
            self.load_gtms()
            
            msg = f"Added {added_count} interventions from Excel"
            if skipped_count > 0:
                msg += f" ({skipped_count} duplicates skipped)"
            
            return rx.toast.success(msg)
            
        except Exception as e:
            return rx.toast.error(f"Failed to load Excel: {str(e)}")

    def add_gtm(self, form_data: dict):
        """Add new GTM to database with validation."""
        try:
            if not form_data.get("UniqueId"):
                return rx.toast.error("UniqueId is required!")
            
            if not form_data.get("PlanningDate"):
                return rx.toast.error("Planning Date is required!")
            
            # Server-side validation of numeric ranges
            is_valid, error_msg = self._validate_numeric_ranges(form_data)
            if not is_valid:
                return rx.toast.error(f"Validation failed: {error_msg}")
            
            # Parse numeric fields
            for field in ["InitialORate", "bo", "Dio", "InitialLRate", "bl", "Dil"]:
                form_data[field] = float(form_data.get(field) or 0)
            
            # Set defaults
            form_data.setdefault("Status", "Plan")
            form_data.setdefault("Category", "")
            form_data.setdefault("Describe", "")
            
            with rx.session() as session:
                existing = session.exec(
                    select(Intervention).where(Intervention.UniqueId == form_data["UniqueId"])
                ).first()
                
                if existing:
                    return rx.toast.error(f"UniqueId '{form_data['UniqueId']}' already exists!")
                
                new_gtm = Intervention(**form_data)
                session.add(new_gtm)
                session.commit()
            
            self.load_gtms()
            return rx.toast.success("GTM added successfully!")
            
        except Exception as e:
            return rx.toast.error(f"Failed to save GTM: {str(e)}")

    def get_gtm(self, gtm: Intervention):
        """Set current GTM for editing."""
        self.current_gtm = gtm

    def update_gtm(self, form_data: dict):
        """Update existing GTM in database with validation."""
        try:
            if not self.current_gtm:
                return rx.toast.error("No intervention selected for update")
            
            unique_id = self.current_gtm.UniqueId
            
            # Server-side validation of numeric ranges
            is_valid, error_msg = self._validate_numeric_ranges(form_data)
            if not is_valid:
                return rx.toast.error(f"Validation failed: {error_msg}")
            
            with rx.session() as session:
                gtm_to_update = session.exec(
                    select(Intervention).where(Intervention.UniqueId == unique_id)
                ).first()
                
                if not gtm_to_update:
                    return rx.toast.error(f"Intervention '{unique_id}' not found")
                
                # Update string fields
                string_fields = ["Field", "Platform", "Reservoir", "TypeGTM",
                               "Category", "PlanningDate", "Status", "Describe"]
                for field in string_fields:
                    value = form_data.get(field)
                    if value is not None and str(value).strip():
                        setattr(gtm_to_update, field, str(value).strip())
                
                # Update numeric fields
                numeric_fields = ["InitialORate", "bo", "Dio", "InitialLRate", "bl", "Dil"]
                for field in numeric_fields:
                    value = form_data.get(field)
                    if value is not None and str(value).strip() != "":
                        try:
                            setattr(gtm_to_update, field, float(value))
                        except (ValueError, TypeError):
                            pass
                
                session.add(gtm_to_update)
                session.commit()
                session.refresh(gtm_to_update)
                self.current_gtm = gtm_to_update
            
            self.load_gtms()
            
            if self.selected_id == unique_id:
                self.intervention_date = self.current_gtm.PlanningDate.split(" ")[0] 
            
            return rx.toast.success(f"Intervention '{unique_id}' updated successfully!")
            
        except Exception as e:
            return rx.toast.error(f"Failed to update GTM: {str(e)}")

    def delete_gtm(self, unique_id: str):
        """Delete GTM from database."""
        try:
            with rx.session() as session:
                gtm_to_delete = session.exec(
                    select(Intervention).where(Intervention.UniqueId == unique_id)
                ).first()
                
                if gtm_to_delete:
                    session.delete(gtm_to_delete)
                    session.commit()
            
            self.load_gtms()
            return rx.toast.success("GTM deleted successfully!")
            
        except Exception as e:
            return rx.toast.error(f"Failed to delete GTM: {str(e)}")

    def transform_data(self):
        """Transform GTM type data for visualization."""
        type_counts = Counter(gtm.TypeGTM for gtm in self.GTM)
        self.gtms_for_graph = [
            {"name": gtm_group, "value": count}
            for gtm_group, count in type_counts.items()
        ]

    # ========== Computed Properties ==========
    
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
    def production_table_data(self) -> List[dict]:
        return self._format_history_for_table(24)
    
    @rx.var
    def forecast_table_data(self) -> List[dict]:
        return self._format_forecast_for_table(12)
    
    @rx.var
    def base_forecast_table_data(self) -> List[dict]:
        """Format base forecast for table display."""
        return [
            {
                "Date": f["date"],
                "OilRate": f"{f['oilRate']:.1f}",
                "LiqRate": f"{f['liqRate']:.1f}",
                "Qoil": f"{f.get('qOil', 0):.0f}",
                "Qliq": f"{f.get('qLiq', 0):.0f}"
            }
            for f in self.base_forecast_data[:12]
        ]
    
    @rx.var
    def base_forecast_totals_display(self) -> str:
        if not self.base_forecast_data:
            return "No base forecast"
        total_qoil = sum(f.get("qOil", 0) for f in self.base_forecast_data)
        total_qliq = sum(f.get("qLiq", 0) for f in self.base_forecast_data)
        return f"Base: Qoil={total_qoil:.0f}t | Qliq={total_qliq:.0f}t"
    
    @rx.var
    def intervention_gain_display(self) -> str:
        """Display gain from intervention vs base."""
        if not self.forecast_data or not self.base_forecast_data:
            return ""
        
        forecast_qoil = sum(f.get("qOil", 0) for f in self.forecast_data)
        base_qoil = sum(f.get("qOil", 0) for f in self.base_forecast_data)
        gain = forecast_qoil - base_qoil
        
        return f"+{gain:.0f}t oil gain" if gain > 0 else f"{gain:.0f}t oil"
    
    @rx.var
    def current_year_total_qoil(self) -> float:
        return sum(row.get("Total", 0) for row in self.current_year_summary)
    
    @rx.var
    def next_year_total_qoil(self) -> float:
        return sum(row.get("Total", 0) for row in self.next_year_summary)
    
    @rx.var
    def current_year_count(self) -> int:
        return len(self.current_year_summary)
    
    @rx.var
    def next_year_count(self) -> int:
        return len(self.next_year_summary)
    @rx.var
    def gtm_type_plotly(self) -> go.Figure:
        """Generate a Plotly bar chart for GTM types."""
        if not self.gtms_for_graph:
            return go.Figure()
            
        names = [d["name"] for d in self.gtms_for_graph]
        values = [d["value"] for d in self.gtms_for_graph]
        
        fig = go.Figure(data=[
            go.Bar(
                x=names, y=values,
                marker_color="#3b82f6",
                text=values,
                textposition='auto',
            )
        ])
        
        fig.update_layout(
            height=250,
            margin=dict(l=20, r=20, t=20, b=20),
            xaxis=dict(tickangle=-45),
            yaxis=dict(title="Count"),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        return fig