"""State management for Production page with DCA forecasting - Optimized."""
import reflex as rx
from typing import Optional
from datetime import datetime, timedelta
import numpy as np
from sqlmodel import select, delete, func, desc

from ..models import (
    CompletionID, 
    HistoryProd, 
    ProductionForecast, 
    Intervention,
    InterventionForecast,
    MAX_PRODUCTION_FORECAST_VERSIONS
)


class ProductionState(rx.State):
    """State for Production monitoring and forecasting.
    
    Optimized for performance with:
    - Background tasks for heavy database operations
    - Separated completion loading from production data loading
    - Cached completion list
    """
    
    # CompletionID data (cached)
    completions: list[CompletionID] = []
    _all_completions: list[CompletionID] = []  # Full cache for filtering
    
    selected_completion: Optional[CompletionID] = None
    selected_unique_id: str = ""
    available_unique_ids: list[str] = []
    
    # History production data (last 5 years)
    history_prod: list[dict] = []
    
    # Forecast parameters and results
    forecast_end_date: str = ""
    forecast_data: list[dict] = []
    
    # Chart data combining actual + forecast
    chart_data: list[dict] = []
    
    # Current forecast version
    current_forecast_version: int = 0
    available_forecast_versions: list[int] = []
    
    # Phase display toggles
    show_oil: bool = True
    show_liquid: bool = True
    show_wc: bool = True  # Water Cut toggle
    
    # Search/filter (local filtering, no DB query)
    search_value: str = ""
    selected_reservoir: str = ""
    
    # DCA parameters (from CompletionID and calculated)
    qi_oil: float = 0.0
    qi_liq: float = 0.0
    dio: float = 0.0
    dil: float = 0.0
    
    # Intervention status for selected well
    has_planned_intervention: bool = False
    intervention_info: str = ""
    
    # Loading states
    is_loading_completions: bool = False
    is_loading_production: bool = False
    
    def toggle_oil(self, checked: bool):
        """Toggle oil phase visibility."""
        self.show_oil = checked
    
    def toggle_liquid(self, checked: bool):
        """Toggle liquid phase visibility."""
        self.show_liquid = checked
    
    def toggle_wc(self, checked: bool):
        """Toggle water cut visibility."""
        self.show_wc = checked

    def load_completions(self):
        """Load all completions from CompletionID table (initial load only)."""
        if self._all_completions:
            # Already loaded, just apply filters
            self._apply_filters()
            return
            
        try:
            self.is_loading_completions = True
            with rx.session() as session:
                self._all_completions = session.exec(select(CompletionID)).all()
            
            self._apply_filters()
            
            # Auto-select first if available
            if self.available_unique_ids and not self.selected_unique_id:
                self.selected_unique_id = self.available_unique_ids[0]
                # Don't auto-load production data on initial load to avoid lag
                
        except Exception as e:
            print(f"Error loading completions: {e}")
            self.completions = []
        finally:
            self.is_loading_completions = False

    def _apply_filters(self):
        """Apply search and reservoir filters to cached completions (no DB query)."""
        filtered = self._all_completions
        
        # Apply search filter
        if self.search_value:
            search_lower = self.search_value.lower()
            filtered = [
                c for c in filtered
                if (c.UniqueId and search_lower in c.UniqueId.lower()) or
                   (c.WellName and search_lower in c.WellName.lower())
            ]
        
        # Apply reservoir filter
        if self.selected_reservoir:
            filtered = [c for c in filtered if c.Reservoir == self.selected_reservoir]
        
        self.completions = filtered
        self.available_unique_ids = [c.UniqueId for c in self.completions]

    def filter_completions(self, search_value: str):
        """Filter completions by search term (local filtering, no DB)."""
        self.search_value = search_value
        self._apply_filters()

    def filter_by_reservoir(self, reservoir: str):
        """Filter by reservoir (local filtering, no DB)."""
        self.selected_reservoir = reservoir if reservoir != "All Reservoirs" else ""
        self._apply_filters()

    def set_selected_unique_id(self, unique_id: str):
        """Set selected completion and trigger background data load."""
        if unique_id == self.selected_unique_id:
            return  # No change, skip reload
            
        self.selected_unique_id = unique_id
        self.forecast_data = []
        self.current_forecast_version = 0
        self.history_prod = []
        self.chart_data = []
        
        # Find completion from cache (no DB query)
        self.selected_completion = next(
            (c for c in self._all_completions if c.UniqueId == unique_id), 
            None
        )
        
        if self.selected_completion:
            self.dio = self.selected_completion.Do if self.selected_completion.Do else 0.0
            self.dil = self.selected_completion.Dl if self.selected_completion.Dl else 0.0
        
        # Load production data in background
        return ProductionState.load_production_data_background

    #@rx.event(background=True)
    async def load_production_data_background(self):
        """Load production data in background to prevent UI blocking."""
        async with self:
            self.is_loading_production = True
        
        try:
            unique_id = None
            async with self:
                unique_id = self.selected_unique_id
            
            if not unique_id:
                return
            
            five_years_ago = datetime.now() - timedelta(days=5*365)
            
            history_data = []
            forecast_versions = []
            has_intervention = False
            intervention_text = ""
            
            with rx.session() as session:
                # Load history production
                history_records = session.exec(
                    select(HistoryProd).where(
                        HistoryProd.UniqueId == unique_id,
                        HistoryProd.Date >= five_years_ago
                    ).order_by(desc(HistoryProd.Date))
                ).all()
                
                for rec in history_records:
                    oil_rate = rec.OilRate if rec.OilRate else 0.0
                    liq_rate = rec.LiqRate if rec.LiqRate else 0.0
                    
                    wc = 0.0
                    if liq_rate > 0:
                        wc = ((liq_rate - oil_rate) / liq_rate) * 100
                        wc = max(0.0, min(100.0, wc))
                    
                    history_data.append({
                        "UniqueId": rec.UniqueId,
                        "Date": rec.Date,
                        "OilRate": oil_rate,
                        "LiqRate": liq_rate,
                        "WC": round(wc, 2),
                        "GOR": rec.GOR if rec.GOR else 0.0,
                        "Dayon": rec.Dayon if rec.Dayon else 0.0,
                        "Method": rec.Method if rec.Method else ""
                    })
                
                # Check for planned intervention
                intervention = session.exec(
                    select(Intervention).where(
                        Intervention.UniqueId == unique_id,
                        Intervention.Status == "Plan"
                    )
                ).first()
                
                has_intervention = intervention is not None
                if intervention:
                    intervention_text = f"{intervention.TypeGTM} planned on {intervention.PlanningDate}"
                
                # Load forecast versions
                forecast_versions = list(session.exec(
                    select(ProductionForecast.Version).where(
                        ProductionForecast.UniqueId == unique_id
                    ).distinct()
                ).all())
            
            # Update state with loaded data
            async with self:
                self.history_prod = history_data
                self.has_planned_intervention = has_intervention
                self.intervention_info = intervention_text
                self.available_forecast_versions = sorted(forecast_versions)
                
                # Calculate qi from last history record
                if self.history_prod:
                    sorted_history = sorted(self.history_prod, key=lambda x: x["Date"])
                    last_record = sorted_history[-1]
                    self.qi_oil = last_record["OilRate"]
                    self.qi_liq = last_record["LiqRate"]
                else:
                    self.qi_oil = 0.0
                    self.qi_liq = 0.0
                
                # Load latest forecast if available
                if self.available_forecast_versions:
                    self.current_forecast_version = max(self.available_forecast_versions)
                
                self.is_loading_production = False
            
            # Load forecast data if version exists
            async with self:
                if self.current_forecast_version > 0:
                    await self._load_forecast_data()
                self._update_chart_data()
                
        except Exception as e:
            print(f"Error loading production data: {e}")
            async with self:
                self.history_prod = []
                self.is_loading_production = False

    async def _load_forecast_data(self):
        """Load forecast data for current version (called from background)."""
        if not self.selected_unique_id or self.current_forecast_version == 0:
            self.forecast_data = []
            return
        
        try:
            with rx.session() as session:
                forecast_records = session.exec(
                    select(ProductionForecast).where(
                        ProductionForecast.UniqueId == self.selected_unique_id,
                        ProductionForecast.Version == self.current_forecast_version
                    ).order_by(ProductionForecast.Date)
                ).all()
                
                self.forecast_data = [
                    {
                        "date": rec.Date.strftime("%Y-%m-%d") if isinstance(rec.Date, datetime) else str(rec.Date),
                        "oilRate": rec.OilRate,
                        "liqRate": rec.LiqRate,
                        "cumOil": rec.Qoil,
                        "cumLiq": rec.Qliq,
                        "wc": rec.WC
                    }
                    for rec in forecast_records
                ]
        except Exception as e:
            print(f"Error loading forecast: {e}")
            self.forecast_data = []

    def load_forecast_from_db(self):
        """Load forecast data synchronously (for version switching)."""
        if not self.selected_unique_id or self.current_forecast_version == 0:
            self.forecast_data = []
            return
        
        try:
            with rx.session() as session:
                forecast_records = session.exec(
                    select(ProductionForecast).where(
                        ProductionForecast.UniqueId == self.selected_unique_id,
                        ProductionForecast.Version == self.current_forecast_version
                    ).order_by(ProductionForecast.Date)
                ).all()
                
                self.forecast_data = [
                    {
                        "date": rec.Date.strftime("%Y-%m-%d") if isinstance(rec.Date, datetime) else str(rec.Date),
                        "oilRate": rec.OilRate,
                        "liqRate": rec.LiqRate,
                        "cumOil": rec.Qoil,
                        "cumLiq": rec.Qliq,
                        "wc": rec.WC
                    }
                    for rec in forecast_records
                ]
        except Exception as e:
            print(f"Error loading forecast: {e}")
            self.forecast_data = []

    def set_forecast_version(self, version: int):
        """Set and load a specific forecast version."""
        self.current_forecast_version = version
        self.load_forecast_from_db()
        self._update_chart_data()

    def set_forecast_version_from_str(self, version_str: str):
        """Convert 'v1' -> 1 and load forecast."""
        if version_str and version_str.startswith("v"):
            version = int(version_str[1:])
            self.set_forecast_version(version)

    def set_forecast_end_date(self, date: str):
        """Set the forecast end date."""
        self.forecast_end_date = date

    def _update_chart_data(self):
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
                "wc": prod["WC"],  # Water Cut from history
                "type": "actual"
            })
        
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

    def _get_next_forecast_version(self, session, unique_id: str) -> int:
        """Determine next forecast version using FIFO logic (max 4 versions)."""
        existing_versions = session.exec(
            select(ProductionForecast.Version, func.min(ProductionForecast.CreatedAt))
            .where(ProductionForecast.UniqueId == unique_id)
            .group_by(ProductionForecast.Version)
        ).all()
        
        if not existing_versions:
            return 1
        
        used_versions = [v[0] for v in existing_versions]
        
        if len(used_versions) < MAX_PRODUCTION_FORECAST_VERSIONS:
            for v in range(1, MAX_PRODUCTION_FORECAST_VERSIONS + 1):
                if v not in used_versions:
                    return v
        
        oldest_version = min(existing_versions, key=lambda x: x[1])[0]
        
        session.exec(
            delete(ProductionForecast).where(
                ProductionForecast.UniqueId == unique_id,
                ProductionForecast.Version == oldest_version
            )
        )
        session.commit()
        
        return oldest_version

    def _save_forecast_to_production_table(self, unique_id: str, forecast_points: list[dict]) -> int:
        """Save forecast to ProductionForecast table with FIFO version control."""
        try:
            with rx.session() as session:
                version = self._get_next_forecast_version(session, unique_id)
                
                cum_oil = 0.0
                cum_liq = 0.0
                prev_date = None
                created_at = datetime.now()
                
                for point in forecast_points:
                    date = datetime.strptime(point["date"], "%Y-%m-%d")
                    oil_rate = point["oilRate"]
                    liq_rate = point["liqRate"]
                    
                    if prev_date:
                        days = (date - prev_date).days
                        cum_oil += oil_rate * days
                        cum_liq += liq_rate * days
                    
                    wc = ((liq_rate - oil_rate) / liq_rate * 100) if liq_rate > 0 else 0
                    
                    prod_record = ProductionForecast(
                        UniqueId=unique_id,
                        Date=date,
                        Version=version,
                        OilRate=oil_rate,
                        LiqRate=liq_rate,
                        Qoil=cum_oil,
                        Qliq=cum_liq,
                        WC=max(0, min(100, wc)),
                        CreatedAt=created_at
                    )
                    session.add(prod_record)
                    prev_date = date
                
                session.commit()
                return version
                
        except Exception as e:
            print(f"Error saving forecast: {e}")
            raise

    def _save_to_intervention_prod(self, unique_id: str, forecast_points: list[dict]):
        """Save forecast to InterventionForecast table as version 0."""
        try:
            with rx.session() as session:
                session.exec(
                    delete(InterventionForecast).where(
                        InterventionForecast.UniqueId == unique_id,
                        InterventionForecast.Version == 0
                    )
                )
                session.commit()
                
                cum_oil = 0.0
                cum_liq = 0.0
                prev_date = None
                created_at = datetime.now()
                
                for point in forecast_points:
                    date = datetime.strptime(point["date"], "%Y-%m-%d")
                    oil_rate = point["oilRate"]
                    liq_rate = point["liqRate"]
                    
                    if prev_date:
                        days = (date - prev_date).days
                        cum_oil += oil_rate * days
                        cum_liq += liq_rate * days
                    
                    wc = ((liq_rate - oil_rate) / liq_rate * 100) if liq_rate > 0 else 0
                    
                    intervention_record = InterventionForecast(
                        UniqueId=unique_id,
                        Date=date,
                        Version=0,
                        DataType="Forecast",
                        OilRate=oil_rate,
                        Qoil=cum_oil,
                        LiqRate=liq_rate,
                        Qliq=cum_liq,
                        WC=max(0, min(100, wc)),
                        CreatedAt=created_at
                    )
                    session.add(intervention_record)
                    prev_date = date
                
                session.commit()
                
        except Exception as e:
            print(f"Error saving to InterventionForecast: {e}")
            raise

    def run_forecast(self):
        """Run Exponential DCA forecast."""
        if not self.selected_completion or not self.forecast_end_date:
            return rx.toast.error("Please select a completion and set forecast end date")
        
        if self.qi_oil <= 0 and self.qi_liq <= 0:
            return rx.toast.error("No production history available")
        
        if self.dio <= 0:
            return rx.toast.error("Invalid decline rate (Di)")
        
        try:
            end_date = datetime.strptime(self.forecast_end_date, "%Y-%m-%d")
            
            sorted_history = sorted(self.history_prod, key=lambda x: x["Date"])
            last_prod = sorted_history[-1]
            
            if isinstance(last_prod["Date"], datetime):
                start_date = last_prod["Date"]
            else:
                start_date = datetime.strptime(str(last_prod["Date"]), "%Y-%m-%d")
            
            if end_date <= start_date:
                return rx.toast.error(f"End date must be after {start_date.strftime('%Y-%m-%d')}")
            
            forecast_points = []
            current_date = start_date + timedelta(days=30)
            t = 1
            
            while current_date <= end_date:
                oil_rate = self.qi_oil * np.exp(-self.dio * t)
                liq_rate = self.qi_liq * np.exp(-self.dil * t)
                
                forecast_points.append({
                    "date": current_date.strftime("%Y-%m-%d"),
                    "oilRate": max(0, round(oil_rate, 2)),
                    "liqRate": max(0, round(liq_rate, 2))
                })
                
                current_date += timedelta(days=30)
                t += 1
            
            if not forecast_points:
                return rx.toast.error("No forecast points generated")
            
            version = self._save_forecast_to_production_table(self.selected_unique_id, forecast_points)
            
            if self.has_planned_intervention:
                self._save_to_intervention_prod(self.selected_unique_id, forecast_points)
            
            self.forecast_data = [
                {"date": p["date"], "oilRate": p["oilRate"], "liqRate": p["liqRate"],
                 "cumOil": 0, "cumLiq": 0, "wc": 0}
                for p in forecast_points
            ]
            self.current_forecast_version = version
            
            with rx.session() as session:
                forecast_versions = list(session.exec(
                    select(ProductionForecast.Version).where(
                        ProductionForecast.UniqueId == self.selected_unique_id
                    ).distinct()
                ).all())
                self.available_forecast_versions = sorted(forecast_versions)
            
            self._update_chart_data()
            
            msg = f"Forecast v{version} saved with {len(forecast_points)} points"
            if self.has_planned_intervention:
                msg += " (also saved to InterventionForecast v0)"
            
            return rx.toast.success(msg)
            
        except Exception as e:
            print(f"Forecast error: {e}")
            return rx.toast.error(f"Forecast failed: {str(e)}")

    def delete_forecast_version(self, version: int):
        """Delete a specific forecast version."""
        if version == 0:
            return rx.toast.error("Cannot delete version 0")
        
        try:
            with rx.session() as session:
                session.exec(
                    delete(ProductionForecast).where(
                        ProductionForecast.UniqueId == self.selected_unique_id,
                        ProductionForecast.Version == version
                    )
                )
                session.commit()
                
                # Reload versions
                forecast_versions = list(session.exec(
                    select(ProductionForecast.Version).where(
                        ProductionForecast.UniqueId == self.selected_unique_id
                    ).distinct()
                ).all())
                self.available_forecast_versions = sorted(forecast_versions)
            
            if self.available_forecast_versions:
                self.current_forecast_version = max(self.available_forecast_versions)
                self.load_forecast_from_db()
            else:
                self.current_forecast_version = 0
                self.forecast_data = []
            
            self._update_chart_data()
            return rx.toast.success(f"Forecast version {version} deleted")
            
        except Exception as e:
            print(f"Delete error: {e}")
            return rx.toast.error(f"Failed to delete: {str(e)}")

    def delete_current_forecast_version(self):
        """Wrapper to delete current version."""
        return self.delete_forecast_version(self.current_forecast_version)

    # ========== Computed Properties ==========
    
    @rx.var
    def total_completions(self) -> int:
        return len(self.completions)
    
    @rx.var
    def unique_reservoirs(self) -> list[str]:
        reservoirs = set(c.Reservoir for c in self._all_completions if c.Reservoir)
        return ["All Reservoirs"] + sorted(reservoirs)
    
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
    def dca_parameters_display(self) -> str:
        return f"qi_o: {self.qi_oil:.1f} | qi_l: {self.qi_liq:.1f} | Dio: {self.dio:.4f} | Dil: {self.dil:.4f}"
    
    @rx.var
    def production_table_data(self) -> list[dict]:
        sorted_data = sorted(self.history_prod, key=lambda x: x["Date"], reverse=True)[:24]
        return [
            {
                "Date": p["Date"].strftime("%Y-%m-%d") if isinstance(p["Date"], datetime) else str(p["Date"]),
                "OilRate": f"{p['OilRate']:.1f}",
                "LiqRate": f"{p['LiqRate']:.1f}",
                "WC": f"{p['WC']:.1f}",
                "WC_val": p['WC']
            }
            for p in sorted_data
        ]
    
    @rx.var
    def forecast_table_data(self) -> list[dict]:
        return [
            {"Date": f["date"], "OilRate": f"{f['oilRate']:.1f}", "LiqRate": f"{f['liqRate']:.1f}", "WC": f"{f['wc']:.1f}"}
            for f in self.forecast_data
        ]
    
    @rx.var
    def forecast_version_options(self) -> list[str]:
        return [f"v{v}" for v in self.available_forecast_versions]
    
    @rx.var
    def current_version_display(self) -> str:
        return f"v{self.current_forecast_version}" if self.current_forecast_version > 0 else ""
    
    @rx.var
    def version_count_display(self) -> str:
        return f"{len(self.available_forecast_versions)}/4"
    
    @rx.var
    def selected_wellname(self) -> str:
        if self.selected_completion and self.selected_completion.WellName:
            return self.selected_completion.WellName
        return "-"
    
    @rx.var
    def selected_reservoir_name(self) -> str:
        if self.selected_completion and self.selected_completion.Reservoir:
            return self.selected_completion.Reservoir
        return "-"
    
    @rx.var
    def completion_info_display(self) -> dict:
        if self.selected_completion:
            return {
                "UniqueId": self.selected_completion.UniqueId,
                "Wellname": self.selected_completion.WellName or "-",
                "Reservoir": self.selected_completion.Reservoir or "-",
                "Completion": self.selected_completion.Completion or "-",
                "kh": f"{self.selected_completion.KH:.1f}" if self.selected_completion.KH else "-",
                "Do": f"{self.selected_completion.Do:.4f}" if self.selected_completion.Do else "-",
                "Dl": f"{self.selected_completion.Dl:.4f}" if self.selected_completion.Dl else "-"
            }
        return {}