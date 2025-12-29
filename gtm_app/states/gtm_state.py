"""Refactored GTM State using DCA Service and Shared State.

This state manages Well Intervention (GTM) operations with improved
code organization using service classes.

DCA Formula: q(t) = qi * exp(-di * 12/365 * t)
For interventions: Qoil = OilRate * K_int * days_in_month

Base Forecast (Version 0): Production decline WITHOUT intervention

Updated: InterventionForecast now uses ID (from InterventionID) as primary key
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
    InterventionID,
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
    "Dio": {"min": 0, "max": 1, "name": "Di (oil)", "unit": "1/month"},
    "Dil": {"min": 0, "max": 1, "name": "Di (liquid)", "unit": "1/month"},
}


class GTMState(SharedForecastState):
    """State for managing Well Intervention (GTM) data.
    
    Inherits common functionality from SharedForecastState.
    
    Key Change: InterventionForecast uses ID (int) as primary key,
    which references InterventionID.ID
    """
    # List of all interventions
    interventions: List[InterventionID] = []
    _all_interventions: List[InterventionID] = []
    
    # Currently selected intervention
    current_intervention: Optional[InterventionID] = None
    selected_id: str = ""  # Format: "ID_UniqueId" e.g., "123_Well-A"
    selected_intervention_id: int = 0  # The actual ID from InterventionID table
    available_ids: List[str] = []
    
    # Base forecast data (version 0 - without intervention)
    base_forecast_data: List[dict] = []
    has_base_forecast: bool = False
    
    # Search/filter state
    search_value: str = ""
    selected_field: str = ""
    selected_status: str = ""
    
    # File upload state
    upload_progress: int = 0
    upload_status: str = ""
    
    # ========== Summary Tables State ==========
    current_year_summary: List[dict] = []
    next_year_summary: List[dict] = []
    current_year: int = datetime.now().year
    next_year: int = datetime.now().year + 1

    # ========== Helper Methods ==========
    
    def _parse_selected_id(self) -> Tuple[int, str]:
        """Parse selected_id string to get ID and UniqueId.
        
        Returns:
            Tuple of (intervention_id: int, unique_id: str)
        """
        if not self.selected_id or "_" not in self.selected_id:
            return 0, ""
        
        parts = self.selected_id.split("_", 1)
        try:
            intervention_id = int(parts[0])
            unique_id = parts[1] if len(parts) > 1 else ""
            return intervention_id, unique_id
        except (ValueError, IndexError):
            return 0, ""

    @staticmethod
    def _validate_numeric_ranges(form_data: dict) -> Tuple[bool, str]:
        """Validate numeric fields are within allowed ranges."""
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
            return False, "; ".join(errors[:3])
        return True, ""

    @staticmethod
    def _validate_excel_row(row: pd.Series, row_index: int) -> Tuple[bool, str]:
        """Validate a row from Excel upload."""
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

    # ========== Load Methods ==========
    
    def load_interventions(self):
        """Load all GTMs from database."""
        try:
            self._load_k_month_data()
            
            with rx.session() as session:
                self._all_interventions = session.exec(select(InterventionID)).all()
            
            self._apply_filters()
            if self.available_ids:
                self.selected_id = self.available_ids[0]
                self.load_production_data()
            
            self.load_forecast_summary_tables()
            
        except Exception as e:
            print(f"Error loading GTMs: {e}")
            self.interventions = []

    def _apply_filters(self):
        """Apply search and filters to interventions list."""
        filtered = self._all_interventions
        if self.search_value:
            search_lower = self.search_value.lower()
            filtered = [
                i for i in filtered
                if (i.UniqueId and search_lower in i.UniqueId.lower()) or
                   (i.Platform and search_lower in i.Platform.lower()) or
                   (i.Field and search_lower in i.Field.lower()) or 
                   (i.Reservoir and search_lower in i.Reservoir.lower()) or
                   (i.Status and search_lower in i.Status.lower())
            ]
        self.interventions = filtered
        # Format: "ID_UniqueId"
        self.available_ids = [f"{i.ID}_{i.UniqueId}" for i in self.interventions]

    def filter_interventions(self, search_values: str):
        """Filter interventions by search term."""
        self.search_value = search_values
        self._apply_filters()

    def load_production_data(self):
        """Load history and forecast production data for selected intervention.
        
        Uses ID for InterventionForecast queries.
        """
        intervention_id, unique_id = self._parse_selected_id()
        
        if not intervention_id:
            self.history_prod = []
            self.chart_data = []
            self.base_forecast_data = []
            self.has_base_forecast = False
            return
        
        self.selected_intervention_id = intervention_id
            
        try:
            with rx.session() as session:
                # Load history using UniqueId (from HistoryProd)
                self.history_prod = DCAService.load_history_data(session, unique_id, years=5)

                # Load forecast versions using ID (from InterventionForecast)
                versions_list = session.exec(
                    select(InterventionForecast.Version).where(
                        InterventionForecast.ID == intervention_id,
                        InterventionForecast.Version >= 1
                    ).distinct()
                ).all()
                
                self.available_forecast_versions = sorted(versions_list)
                
                # Check base forecast exists using ID
                base_exists = session.exec(
                    select(InterventionForecast.ID).where(
                        InterventionForecast.ID == intervention_id,
                        InterventionForecast.Version == 0
                    ).limit(1)
                ).first()
                self.has_base_forecast = base_exists is not None
            
            # Find current intervention from list
            selected_gtm = next(
                (g for g in self.interventions if g.ID == intervention_id), None
            )
            if selected_gtm:
                self.intervention_date = selected_gtm.PlanningDate.split(" ")[0] 
                self.current_intervention = selected_gtm
            
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
        """Load base forecast (version 0) from database using ID."""
        intervention_id, _ = self._parse_selected_id()
        
        if not intervention_id:
            self.base_forecast_data = []
            self.has_base_forecast = False
            return
            
        try:
            with rx.session() as session:
                records = session.exec(
                    select(InterventionForecast).where(
                        InterventionForecast.ID == intervention_id,
                        InterventionForecast.Version == 0
                    ).order_by(InterventionForecast.Date)
                ).all()
                
                self.base_forecast_data = [
                    {
                        "date": rec.Date.strftime("%Y-%m-%d") if isinstance(rec.Date, datetime) else str(rec.Date),
                        "oilRate": rec.OilRate,
                        "liqRate": rec.LiqRate,
                        "qOil": rec.Qoil,
                        "qLiq": rec.Qliq,
                        "wc": rec.WC
                    }
                    for rec in records
                ]
                self.has_base_forecast = len(self.base_forecast_data) > 0
        except Exception as e:
            print(f"Error loading base forecast: {e}")
            self.base_forecast_data = []
            self.has_base_forecast = False

    def load_forecast_from_db(self):
        """Load forecast data for current version from database using ID."""
        intervention_id, _ = self._parse_selected_id()
        
        if not intervention_id or self.current_forecast_version == 0:
            self.forecast_data = []
            return
        
        try:
            with rx.session() as session:
                records = session.exec(
                    select(InterventionForecast).where(
                        InterventionForecast.ID == intervention_id,
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
                    for rec in records
                ]
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

    def set_forecast_version(self, version_str: str):
        """Set forecast version from string."""
        if version_str and version_str.startswith("v"):
            self.current_forecast_version = int(version_str[1:])
            self.load_forecast_from_db()
            self._update_chart_with_base()

    def set_selected_id(self, id_value: str):
        """Set selected intervention ID."""
        self.selected_id = id_value
        self.forecast_data = []
        self.base_forecast_data = []
        self.current_forecast_version = 0
        self.has_base_forecast = False
        self.load_production_data()

    # ========== Forecast Methods ==========

    def run_forecast(self):
        """Run Arps decline curve forecast for intervention."""
        if not self.current_intervention or not self.forecast_end_date:
            return rx.toast.error("Please select an intervention and set forecast end date")
        
        intervention_id, unique_id = self._parse_selected_id()
        if not intervention_id:
            return rx.toast.error("Invalid intervention selected")
        
        try:
            qi_oil = self.current_intervention.InitialORate
            b_oil = self.current_intervention.bo
            di_oil = self.current_intervention.Dio
            qi_liq = self.current_intervention.InitialLRate
            b_liq = self.current_intervention.bl
            di_liq = self.current_intervention.Dil
            
            end_date = datetime.strptime(self.forecast_end_date, "%Y-%m-%d")
            
            if self.current_intervention.Status == "Plan":
                start_date = datetime.strptime(self.current_intervention.PlanningDate, "%Y-%m-%d")
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
            
            # Save forecast using ID
            with rx.session() as session:
                version = self._get_next_version_fifo(session, intervention_id)
                self._save_forecast_to_db(
                    session, intervention_id,unique_id, result.forecast_points, version
                )
            
            self.forecast_data = DCAService.forecast_to_dict_list(result.forecast_points)
            self.current_forecast_version = version
            
            # Refresh available versions
            with rx.session() as session:
                versions_list = session.exec(
                    select(InterventionForecast.Version).where(
                        InterventionForecast.ID == intervention_id,
                        InterventionForecast.Version >= 1
                    ).distinct()
                ).all()
                self.available_forecast_versions = sorted(versions_list)
            
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

    def _get_next_version_fifo(self, session, intervention_id: int) -> int:
        """Get next forecast version using FIFO logic with ID."""
        existing_versions = session.exec(
            select(InterventionForecast.Version, func.min(InterventionForecast.CreatedAt))
            .where(
                InterventionForecast.ID == intervention_id,
                InterventionForecast.Version >= 1
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
        
        # Delete oldest version
        oldest_version = min(existing_versions, key=lambda x: x[1])[0]
        session.exec(
            delete(InterventionForecast).where(
                InterventionForecast.ID == intervention_id,
                InterventionForecast.Version == oldest_version
            )
        )
        session.commit()
        
        return oldest_version

    def _save_forecast_to_db(self, session, intervention_id: int,UniqueId:str, forecast_points, version: int):
        """Save forecast points to database using ID."""
        from ..utils.dca_utils import ForecastPoint
        
        created_at = datetime.now()
        
        # Delete existing records for this version
        session.exec(
            delete(InterventionForecast).where(
                InterventionForecast.ID == intervention_id,
                InterventionForecast.Version == version
            )
        )
        session.commit()
        
        for fp in forecast_points:
            record = InterventionForecast(
                ID=intervention_id,
                UniqueId=UniqueId,
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
            session.add(record)
        
        session.commit()

    def delete_forecast_version(self):
        """Delete a specific forecast version using ID."""
        version = self.current_forecast_version
        if version == 0:
            return rx.toast.error("Cannot delete base case forecast (version 0)")
        
        intervention_id, _ = self._parse_selected_id()
        if not intervention_id:
            return rx.toast.error("No intervention selected")
        
        try:
            with rx.session() as session:
                session.exec(
                    delete(InterventionForecast).where(
                        InterventionForecast.ID == intervention_id,
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
        """Delete the currently selected forecast version."""
        return self.delete_forecast_version()

    # ========== Summary Tables ==========

    def set_year(self, year: int) -> int:
        """Set current year and return it."""
        self.current_year = int(year)
        return self.current_year

    def load_forecast_summary_tables(self):
        """Load forecast summary data for current year and next year.
        
        Logic:
        1. For 2025: Select interventions where InterventionYear = 2025
        - Get latest forecast version for each
        - Sum Qoil by month for 2025 only
        2. For 2026: Select interventions where InterventionYear = 2026
        - Get latest forecast version for each
        - Sum Qoil by month for 2026 only
        3. Add total row summing each month
        """
        try:
            current_year = 2025
            next_year = 2026
            
            self.current_year = current_year
            self.next_year = next_year
            
            month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            
            with rx.session() as session:
                # Get all interventions
                all_interventions = session.exec(select(InterventionID)).all()
                
                # Filter interventions by InterventionYear
                interventions_2025 = [g for g in self._all_interventions if g.InterventionYear == current_year]
                interventions_2026 = [g for g in self._all_interventions if g.InterventionYear == next_year]
                
                # Create lookup dictionaries
                intervention_dict_2025 = {
                    gtm.UniqueId: {
                        "Field": gtm.Field,
                        "Platform": gtm.Platform,
                        "Reservoir": gtm.Reservoir,
                        "Type": gtm.TypeGTM,
                        "Category": gtm.Category,
                        "Status": gtm.Status,
                        "Date": gtm.PlanningDate,
                        "GTMYear": gtm.InterventionYear
                    }
                    for gtm in interventions_2025
                }
                
                intervention_dict_2026 = {
                    gtm.UniqueId: {
                        "Field": gtm.Field,
                        "Platform": gtm.Platform,
                        "Reservoir": gtm.Reservoir,
                        "Type": gtm.TypeGTM,
                        "Category": gtm.Category,
                        "Status": gtm.Status,
                        "Date": gtm.PlanningDate,
                        "GTMYear": gtm.InterventionYear
                    }
                    for gtm in interventions_2026
                }
                
                # Get all forecast records with Version > 0
                forecast_records = session.exec(
                    select(InterventionForecast).where(InterventionForecast.Version > 0)
                ).all()
                
                # Group forecasts by UniqueId and Version
                forecast_by_uid: Dict[str, Dict[int, List]] = {}
                for rec in forecast_records:
                    uid = rec.UniqueId
                    ver = rec.Version
                    if uid not in forecast_by_uid:
                        forecast_by_uid[uid] = {}
                    if ver not in forecast_by_uid[uid]:
                        forecast_by_uid[uid][ver] = []
                    forecast_by_uid[uid][ver].append(rec)
                
                # Process 2025 interventions
                current_year_data = []
                current_year_totals = {m: 0.0 for m in range(1, 13)}
                
                for uid in intervention_dict_2025.keys():
                    if uid not in forecast_by_uid:
                        continue
                    
                    versions = forecast_by_uid[uid]
                    latest_version = max(versions.keys())
                    records = versions[latest_version]
                    details = intervention_dict_2025[uid]
                    
                    # Monthly Qoil for current year only
                    monthly_qoil = {m: 0.0 for m in range(1, 13)}
                    
                    for rec in records:
                        rec_date = rec.Date if isinstance(rec.Date, datetime) else datetime.strptime(str(rec.Date), "%Y-%m-%d")
                        rec_year = rec_date.year
                        rec_month = rec_date.month
                        qoil = rec.Qoil if rec.Qoil else 0.0
                        
                        # Only sum Qoil for current_year (2025)
                        if rec_year == current_year:
                            monthly_qoil[rec_month] += qoil
                    
                    # Build row
                    row = {
                        "UniqueId": uid,
                        "Field": details["Field"],
                        "Platform": details["Platform"],
                        "Reservoir": details["Reservoir"],
                        "Type": details["Type"],
                        "Category": details["Category"],
                        "Status": details["Status"],
                        "Date": details["Date"],
                        "GTMYear": details["GTMYear"],
                    }
                    
                    for i, name in enumerate(month_names, 1):
                        row[name] = round(monthly_qoil[i], 1)
                        current_year_totals[i] += monthly_qoil[i]
                    
                    row["Total"] = round(sum(monthly_qoil.values()) / 1000, 1)  # in thousands
                    
                    if sum(monthly_qoil.values()) > 0:
                        current_year_data.append(row)
                
                # Add total row for 2025
                if current_year_data:
                    total_row = {
                        "UniqueId": "TOTAL",
                        "Field": "-",
                        "Platform": "-",
                        "Reservoir": "-",
                        "Type": "-",
                        "Category": "-",
                        "Status": "-",
                        "Date": "-",
                        "GTMYear": current_year,
                    }
                    for i, name in enumerate(month_names, 1):
                        total_row[name] = round(current_year_totals[i], 1)
                    total_row["Total"] = round(sum(current_year_totals.values()) / 1000, 1)
                    current_year_data.append(total_row)
                
                # Process 2026 interventions
                next_year_data = []
                next_year_totals = {m: 0.0 for m in range(1, 13)}
                
                for uid in intervention_dict_2026.keys():
                    if uid not in forecast_by_uid:
                        continue
                    
                    versions = forecast_by_uid[uid]
                    latest_version = max(versions.keys())
                    records = versions[latest_version]
                    details = intervention_dict_2026[uid]
                    
                    # Monthly Qoil for next year only
                    monthly_qoil = {m: 0.0 for m in range(1, 13)}
                    
                    for rec in records:
                        rec_date = rec.Date if isinstance(rec.Date, datetime) else datetime.strptime(str(rec.Date), "%Y-%m-%d")
                        rec_year = rec_date.year
                        rec_month = rec_date.month
                        qoil = rec.Qoil if rec.Qoil else 0.0
                        
                        # Only sum Qoil for next_year (2026)
                        if rec_year == next_year:
                            monthly_qoil[rec_month] += qoil
                    
                    # Build row
                    row = {
                        "UniqueId": uid,
                        "Field": details["Field"],
                        "Platform": details["Platform"],
                        "Reservoir": details["Reservoir"],
                        "Type": details["Type"],
                        "Category": details["Category"],
                        "Status": details["Status"],
                        "Date": details["Date"],
                        "GTMYear": details["GTMYear"],
                    }
                    
                    for i, name in enumerate(month_names, 1):
                        row[name] = round(monthly_qoil[i], 1)
                        next_year_totals[i] += monthly_qoil[i]
                    
                    row["Total"] = round(sum(monthly_qoil.values()) / 1000, 1)
                    
                    if sum(monthly_qoil.values()) > 0:
                        next_year_data.append(row)
                
                # Add total row for 2026
                if next_year_data:
                    total_row = {
                        "UniqueId": "TOTAL",
                        "Field": "-",
                        "Platform": "-",
                        "Reservoir": "-",
                        "Type": "-",
                        "Category": "-",
                        "Status": "-",
                        "Date": "-",
                        "GTMYear": next_year,
                    }
                    for i, name in enumerate(month_names, 1):
                        total_row[name] = round(next_year_totals[i], 1)
                    total_row["Total"] = round(sum(next_year_totals.values()) / 1000, 1)
                    next_year_data.append(total_row)
                
                # Sort by UniqueId (TOTAL will be at end due to alphabetical sorting)
                self.current_year_summary = sorted(
                    current_year_data, 
                    key=lambda x: (x["UniqueId"] == "TOTAL", x["UniqueId"])
                )
                self.next_year_summary = sorted(
                    next_year_data, 
                    key=lambda x: (x["UniqueId"] == "TOTAL", x["UniqueId"])
                )
                
        except Exception as e:
            print(f"Error loading forecast summary: {e}")
            import traceback
            traceback.print_exc()
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

    # ========== CRUD Operations ==========

    def add_intervention(self, form_data: dict):
        """Add new GTM to database with validation."""
        try:
            if not form_data.get("UniqueId"):
                return rx.toast.error("UniqueId is required!")
            
            if not form_data.get("PlanningDate"):
                return rx.toast.error("Planning Date is required!")
            
            is_valid, error_msg = self._validate_numeric_ranges(form_data)
            if not is_valid:
                return rx.toast.error(f"Validation failed: {error_msg}")
            
            for field in ["InitialORate", "bo", "Dio", "InitialLRate", "bl", "Dil"]:
                form_data[field] = float(form_data.get(field) or 0)
            
            form_data.setdefault("Status", "Plan")
            form_data.setdefault("Category", "")
            form_data.setdefault("Describe", "")
            form_data["InterventionYear"] = datetime.strptime(form_data["PlanningDate"], "%Y-%m-%d").year
            
            with rx.session() as session:
                new_gtm = InterventionID(**form_data)
                session.add(new_gtm)
                session.commit()
            
            self.load_interventions()
            return rx.toast.success("GTM added successfully!")
            
        except Exception as e:
            return rx.toast.error(f"Failed to save GTM: {str(e)}")

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
                'PlanningDate', 'InterventionYear', 'Status', 'InitialORate', 'bo', 'Dio',
                'InitialLRate', 'bl', 'Dil'
            ]
            
            missing_cols = [c for c in required_cols if c not in df.columns]
            if missing_cols:
                return rx.toast.error(f"Missing columns: {', '.join(missing_cols)}")
            
            validation_errors = []
            for idx, row in df.iterrows():
                is_valid, error_msg = self._validate_excel_row(row, idx + 2)
                if not is_valid:
                    validation_errors.append(error_msg)
            
            if validation_errors:
                error_summary = "; ".join(validation_errors[:5])
                if len(validation_errors) > 5:
                    error_summary += f" ... and {len(validation_errors) - 5} more errors"
                return rx.toast.error(f"Validation failed: {error_summary}")
            
            added_count = 0
            
            with rx.session() as session:
                for _, row in df.iterrows():
                    new_gtm = InterventionID(
                        UniqueId=str(row['UniqueId']),
                        Field=str(row['Field']),
                        Platform=str(row['Platform']),
                        Reservoir=str(row['Reservoir']),
                        TypeGTM=str(row['TypeGTM']),
                        Category=str(row.get('Category', '')),
                        PlanningDate=str(row['PlanningDate'])[:10],
                        InterventionYear=int(row['InterventionYear']),
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
            
            self.load_interventions()
            return rx.toast.success(f"Added {added_count} interventions from Excel")
            
        except Exception as e:
            return rx.toast.error(f"Failed to load Excel: {str(e)}")

    def get_gtm(self, intervention: InterventionID):
        """Set current GTM for editing."""
        self.current_intervention = intervention

    def update_intervention(self, form_data: dict):
        """Update existing GTM in database with validation."""
        try:
            if not self.current_intervention:
                return rx.toast.error("No intervention selected for update")
            
            intervention_id = self.current_intervention.ID
            unique_id = self.current_intervention.UniqueId
            
            is_valid, error_msg = self._validate_numeric_ranges(form_data)
            if not is_valid:
                return rx.toast.error(f"Validation failed: {error_msg}")
            
            with rx.session() as session:
                gtm_to_update = session.exec(
                    select(InterventionID).where(InterventionID.ID == intervention_id)
                ).first()
                
                if not gtm_to_update:
                    return rx.toast.error(f"Intervention ID '{intervention_id}' not found")
                
                string_fields = ["Field", "Platform", "Reservoir", "TypeGTM",
                               "Category", "PlanningDate", "Status", "Describe"]
                for field in string_fields:
                    value = form_data.get(field)
                    if value is not None and str(value).strip():
                        setattr(gtm_to_update, field, str(value).strip())
                
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
                self.current_intervention = gtm_to_update
            
            self.load_interventions()
            
            current_id, _ = self._parse_selected_id()
            if current_id == intervention_id:
                self.intervention_date = self.current_intervention.PlanningDate
            
            return rx.toast.success(f"Intervention '{unique_id}' updated successfully!")
            
        except Exception as e:
            return rx.toast.error(f"Failed to update Intervention: {str(e)}")

    def delete_intervention(self, unique_id: str):
        """Delete GTM from database."""
        try:
            with rx.session() as session:
                gtm_to_delete = session.exec(
                    select(InterventionID).where(InterventionID.UniqueId == unique_id)
                ).first()
                
                if gtm_to_delete:
                    # Also delete associated forecasts
                    session.exec(
                        delete(InterventionForecast).where(
                            InterventionForecast.ID == gtm_to_delete.ID
                        )
                    )
                    session.delete(gtm_to_delete)
                    session.commit()
            
            self.load_interventions()
            return rx.toast.success("GTM deleted successfully!")
            
        except Exception as e:
            return rx.toast.error(f"Failed to delete GTM: {str(e)}")

    # ========== Computed Properties ==========
    
    @rx.var
    def GTM(self) -> List[InterventionID]:
        """Alias for interventions list (for compatibility with UI components)."""
        return self.interventions
    
    @rx.var
    def current_gtm(self) -> Optional[InterventionID]:
        """Alias for current_intervention."""
        return self.current_intervention
    
    @rx.var
    def total_interventions(self) -> int:
        return len(self.interventions)
    
    @rx.var
    def planned_interventions(self) -> int:
        return sum(1 for gtm in self.interventions if gtm.Status == "Plan")
    
    @rx.var
    def completed_interventions(self) -> int:
        return sum(1 for gtm in self.interventions if gtm.Status == "Done")
    
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