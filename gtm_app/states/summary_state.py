"""State management for Production Summary Page.

Combines HistoryProd and ProductionForecast data into monthly summaries.
For a given year, history months are taken from HistoryProd,
forecast months are taken from ProductionForecast.
"""
import reflex as rx
from sqlmodel import select, func
from datetime import datetime
from typing import List, Dict, Any, Optional
import pandas as pd
import io

from ..models import HistoryProd, ProductionForecast, CompletionID, WellID


class SummaryState(rx.State):
    """State for Production Summary page."""
    
    # Filter selections
    selected_year: int = 2025
    selected_metric: str = "rate"  # "rate" or "Q"
    selected_phase: str = "oil"    # "oil" or "liquid"
    
    # Data storage
    summary_data: List[Dict[str, Any]] = []
    is_loading: bool = False
    
    # Year options
    year_options: List[str] = [str(y) for y in range(2025, 2051)]
    
    # Current date for reference
    _current_date: datetime = datetime.now()
    
    @rx.var
    def metric_options(self) -> List[str]:
        """Get metric options."""
        return ["rate", "Q"]
    
    @rx.var
    def phase_options(self) -> List[str]:
        """Get phase options."""
        return ["oil", "liquid"]
    
    @rx.var
    def current_year_str(self) -> str:
        """Current year as string."""
        return str(self.selected_year)
    
    @rx.var
    def table_title(self) -> str:
        """Dynamic table title based on selections."""
        metric_label = "Rate (t/d)" if self.selected_metric == "rate" else "Cumulative (t)"
        phase_label = "Oil" if self.selected_phase == "oil" else "Liquid"
        return f"{phase_label} {metric_label} - {self.selected_year}"
    
    @rx.var
    def summary_count(self) -> int:
        """Count of rows in summary."""
        return len(self.summary_data)
    
    @rx.var
    def total_value(self) -> str:
        """Calculate total for the year."""
        if not self.summary_data:
            return "0"
        
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", 
                  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        total = 0.0
        for row in self.summary_data:
            if row.get("UniqueId") == "TOTAL":
                continue
            for month in months:
                val = row.get(month, 0)
                if isinstance(val, (int, float)):
                    total += val
                elif isinstance(val, str):
                    try:
                        total += float(val) if val and val != "-" else 0
                    except ValueError:
                        pass
        return f"{total:,.1f}"
    
    def set_selected_year(self, year: str):
        """Set selected year and reload data."""
        self.selected_year = int(year)
        return SummaryState.load_summary_data
    
    def set_selected_metric(self, metric: str):
        """Set selected metric and reload data."""
        self.selected_metric = metric
        return SummaryState.load_summary_data
    
    def set_selected_phase(self, phase: str):
        """Set selected phase and reload data."""
        self.selected_phase = phase
        return SummaryState.load_summary_data
    
    @rx.event(background=True)
    async def load_summary_data(self):
        """Load and merge history and forecast data for the selected year.
        
        Values are multiplied by VSPShare from WellID table.
        VSPShare represents the ownership share (0-1) for production allocation.
        
        Data source logic:
        - Months <= last history month: from HistoryProd
        - Months > last history month: from ProductionForecast
        """
        async with self:
            self.is_loading = True
        
        try:
            year = None
            metric = None
            phase = None
            
            async with self:
                year = self.selected_year
                metric = self.selected_metric
                phase = self.selected_phase
            
            summary_result = []
            
            with rx.session() as session:
                # First, find the last month of history data
                from sqlmodel import func
                last_history_date = session.exec(
                    select(func.max(HistoryProd.Date))
                ).one_or_none()
                
                if last_history_date:
                    last_history_year = last_history_date.year
                    last_history_month = last_history_date.month
                else:
                    # No history data - all from forecast
                    last_history_year = 0
                    last_history_month = 0
                
                # Determine current_month for the selected year
                # This is the last month that should come from history
                if year < last_history_year:
                    # Past year - all 12 months from history
                    current_month = 12
                elif year == last_history_year:
                    # Same year as last history - use last history month
                    current_month = last_history_month
                else:
                    # Future year - no history, all from forecast
                    current_month = 0
                
                # Get all completions joined with WellID to get VSPShare
                # CompletionID.WellName -> WellID.WellName
                completions_with_vsp = session.exec(
                    select(CompletionID, WellID.VSPShare, WellID.Field, WellID.Platform).join(
                        WellID, CompletionID.WellName == WellID.WellName
                    ).order_by(CompletionID.UniqueId)
                ).all()
                
                if not completions_with_vsp:
                    # Fallback: load completions without VSPShare (use 1.0)
                    completions = session.exec(
                        select(CompletionID).order_by(CompletionID.UniqueId)
                    ).all()
                    completions_with_vsp = [(c, 1.0, "", "") for c in completions]
                
                if not completions_with_vsp:
                    async with self:
                        self.summary_data = []
                        self.is_loading = False
                    return
                
                # Create lookup dictionaries
                completion_lookup = {}
                vsp_lookup = {}
                field_lookup = {}
                platform_lookup = {}
                unique_ids = []
                
                for comp, vsp_share, field, platform in completions_with_vsp:
                    uid = comp.UniqueId
                    unique_ids.append(uid)
                    completion_lookup[uid] = comp
                    vsp_lookup[uid] = vsp_share if vsp_share else 1.0
                    field_lookup[uid] = field if field else "-"
                    platform_lookup[uid] = platform if platform else "-"
                
                # Define date range for the year
                year_start = datetime(year, 1, 1)
                year_end = datetime(year, 12, 31)
                
                # Load history data for the year
                history_records = session.exec(
                    select(HistoryProd).where(
                        HistoryProd.Date >= year_start,
                        HistoryProd.Date <= year_end
                    )
                ).all()
                
                # Load forecast data for the year (use latest version per UniqueId)
                forecast_records = session.exec(
                    select(ProductionForecast).where(
                        ProductionForecast.Date >= year_start,
                        ProductionForecast.Date <= year_end
                    )
                ).all()
                
                # Group history by UniqueId and month
                history_by_uid: Dict[str, Dict[int, Dict]] = {}
                for rec in history_records:
                    uid = rec.UniqueId
                    month = rec.Date.month
                    if uid not in history_by_uid:
                        history_by_uid[uid] = {}
                    
                    # Store the values (raw, before VSPShare)
                    history_by_uid[uid][month] = {
                        "OilRate": rec.OilRate or 0,
                        "LiqRate": rec.LiqRate or 0,
                        "Qoil": rec.Qoil or 0,
                        "Qliq": (rec.Qoil or 0) + (rec.Qwater or 0)  # Qliq = Qoil + Qwater
                    }
                
                # Group forecast by UniqueId and month (use max version)
                forecast_by_uid: Dict[str, Dict[int, Dict]] = {}
                version_by_uid: Dict[str, int] = {}
                
                for rec in forecast_records:
                    uid = rec.UniqueId
                    version = rec.Version
                    
                    # Track max version per UniqueId
                    if uid not in version_by_uid or version > version_by_uid[uid]:
                        version_by_uid[uid] = version
                
                # Now filter to only max version records
                for rec in forecast_records:
                    uid = rec.UniqueId
                    if rec.Version != version_by_uid.get(uid, 0):
                        continue
                    
                    month = rec.Date.month
                    if uid not in forecast_by_uid:
                        forecast_by_uid[uid] = {}
                    
                    forecast_by_uid[uid][month] = {
                        "OilRate": rec.OilRate or 0,
                        "LiqRate": rec.LiqRate or 0,
                        "Qoil": rec.Qoil or 0,
                        "Qliq": rec.Qliq or 0
                    }
                
                # Build summary rows
                month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
                
                # Totals for each month
                monthly_totals = {m: 0.0 for m in month_names}
                
                for uid in unique_ids:
                    completion = completion_lookup.get(uid)
                    vsp_share = vsp_lookup.get(uid, 1.0)
                    
                    row = {
                        "UniqueId": uid,
                        "WellName": completion.WellName if completion else "-",
                        "Reservoir": completion.Reservoir if completion else "-",
                        "Field": field_lookup.get(uid, "-"),
                        "Platform": platform_lookup.get(uid, "-"),
                        "VSPShare": round(vsp_share * 100, 1),  # Display as percentage
                    }
                    
                    row_total = 0.0
                    
                    for month_idx, month_name in enumerate(month_names, 1):
                        # Determine data source based on last history month
                        # month_idx <= current_month: use history
                        # month_idx > current_month: use forecast
                        value = 0.0
                        
                        if month_idx <= current_month:
                            # Use history data
                            if uid in history_by_uid:
                                month_data = history_by_uid[uid].get(month_idx, {})
                                if metric == "rate":
                                    value = month_data.get("OilRate" if phase == "oil" else "LiqRate", 0)
                                else:  # Q
                                    value = month_data.get("Qoil" if phase == "oil" else "Qliq", 0)
                        else:
                            # Use forecast data
                            if uid in forecast_by_uid:
                                month_data = forecast_by_uid[uid].get(month_idx, {})
                                if metric == "rate":
                                    value = month_data.get("OilRate" if phase == "oil" else "LiqRate", 0)
                                else:  # Q
                                    value = month_data.get("Qoil" if phase == "oil" else "Qliq", 0)
                        
                        # Apply VSPShare multiplication
                        value = value * vsp_share
                        
                        # Format value
                        if value == 0:
                            row[month_name] = "-"
                        else:
                            row[month_name] = round(value, 1)
                            row_total += value
                            monthly_totals[month_name] += value
                    
                    row["Total"] = round(row_total, 1) if row_total > 0 else "-"
                    summary_result.append(row)
                
                # Add total row
                total_row = {
                    "UniqueId": "TOTAL",
                    "WellName": "-",
                    "Reservoir": "-",
                    "Field": "-",
                    "Platform": "-",
                    "VSPShare": "-",
                }
                grand_total = 0.0
                for month_name in month_names:
                    val = monthly_totals[month_name]
                    total_row[month_name] = round(val, 1) if val > 0 else "-"
                    grand_total += val
                total_row["Total"] = round(grand_total, 1) if grand_total > 0 else "-"
                summary_result.append(total_row)
            
            async with self:
                self.summary_data = summary_result
                self.is_loading = False
                
        except Exception as e:
            print(f"Error loading summary data: {e}")
            import traceback
            traceback.print_exc()
            async with self:
                self.summary_data = []
                self.is_loading = False
    
    def download_summary_excel(self):
        """Download summary data as Excel file."""
        if not self.summary_data:
            return rx.toast.error("No data to download")
        
        try:
            columns = ["UniqueId", "WellName", "Field", "Platform", "Reservoir", "VSPShare",
                      "Jan", "Feb", "Mar", "Apr", "May", "Jun",
                      "Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Total"]
            
            df = pd.DataFrame(self.summary_data)
            # Ensure all columns exist
            for col in columns:
                if col not in df.columns:
                    df[col] = "-"
            df = df[columns]
            
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                phase_label = "Oil" if self.selected_phase == "oil" else "Liquid"
                metric_label = "Rate" if self.selected_metric == "rate" else "Q"
                sheet_name = f"{phase_label}_{metric_label}_{self.selected_year}"
                df.to_excel(writer, sheet_name=sheet_name[:31], index=False)
            
            output.seek(0)
            filename = f"Production_Summary_{phase_label}_{metric_label}_{self.selected_year}.xlsx"
            
            return rx.download(
                data=output.getvalue(),
                filename=filename,
            )
            
        except Exception as e:
            return rx.toast.error(f"Download failed: {str(e)}")