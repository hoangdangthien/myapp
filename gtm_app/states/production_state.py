"""State management for Production page with DCA forecasting - Using elapsed days pattern."""
import reflex as rx
from typing import Optional, Dict
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from sqlmodel import select, delete, func, desc

from ..models import (
    CompletionID, 
    HistoryProd, 
    ProductionForecast, 
    Intervention,
    InterventionForecast,
    KMonth,
    MAX_PRODUCTION_FORECAST_VERSIONS
)
from ..utils.dca_utils import (
    arps_exponential,
    arps_decline,
    generate_forecast_dates,
    calculate_water_cut,
    run_dca_forecast,
    ForecastPoint,
)


class ProductionState(rx.State):
    """State for Production monitoring and forecasting.
    
    DCA Formula: q(t) = qi * exp(-di * 12/365 * t)
    Where:
    - qi = Initial rate (t/day)
    - di = Decline rate (1/year)  
    - t = Elapsed days from start
    
    Cumulative: Qoil = OilRate * K_oil * days_in_month
    """
    
    # CompletionID data (cached)
    completions: list[CompletionID] = []
    _all_completions: list[CompletionID] = []
    
    selected_completion: Optional[CompletionID] = None
    selected_unique_id: str = ""
    available_unique_ids: list[str] = []
    
    # Current completion for editing
    current_completion: Optional[CompletionID] = None
    
    # History production data (last 5 years)
    history_prod: list[dict] = []
    
    # KMonth data cache {month_id: {K_oil, K_liq, K_int, K_inj}}
    k_month_data: dict = {}
    
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
    show_wc: bool = True
    
    # Search/filter
    search_value: str = ""
    selected_reservoir: str = ""
    
    # DCA parameters from CompletionID
    qi_oil: float = 0.0
    qi_liq: float = 0.0
    dio: float = 0.0  # Decline rate for oil (1/year)
    dil: float = 0.0  # Decline rate for liquid (1/year)
    b_oil: float = 0.0  # Decline exponent for oil
    b_liq: float = 0.0  # Decline exponent for liquid
    
    # Intervention status
    has_planned_intervention: bool = False
    intervention_info: str = ""
    
    # Loading states
    is_loading_completions: bool = False
    is_loading_production: bool = False
    
    # DCA mode selection (True=Exponential, False=Hyperbolic)
    use_exponential_dca: bool = True
    
    def toggle_oil(self, checked: bool):
        self.show_oil = checked
    
    def toggle_liquid(self, checked: bool):
        self.show_liquid = checked
    
    def toggle_wc(self, checked: bool):
        self.show_wc = checked
    
    def set_dca_mode(self, use_exponential: bool):
        """Toggle between Exponential and Hyperbolic DCA."""
        self.use_exponential_dca = use_exponential

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
                
            # If no KMonth data, use defaults
            if not self.k_month_data:
                self.k_month_data = {
                    i: {"K_oil": 1.0, "K_liq": 1.0, "K_int": 1.0, "K_inj": 1.0} 
                    for i in range(1, 13)
                }
        except Exception as e:
            print(f"Error loading KMonth data: {e}")
            self.k_month_data = {
                i: {"K_oil": 1.0, "K_liq": 1.0, "K_int": 1.0, "K_inj": 1.0} 
                for i in range(1, 13)
            }

    def load_completions(self):
        """Load all completions from CompletionID table."""
        try:
            self.is_loading_completions = True
            
            # Load KMonth data first
            self.load_k_month_data()
            
            with rx.session() as session:
                self._all_completions = session.exec(select(CompletionID)).all()
            
            self._apply_filters()
            
            if self.available_unique_ids and not self.selected_unique_id:
                self.selected_unique_id = self.available_unique_ids[0]
                
        except Exception as e:
            print(f"Error loading completions: {e}")
            self.completions = []
        finally:
            self.is_loading_completions = False

    def _apply_filters(self):
        """Apply search and reservoir filters to cached completions."""
        filtered = self._all_completions
        
        if self.search_value:
            search_lower = self.search_value.lower()
            filtered = [
                c for c in filtered
                if (c.UniqueId and search_lower in c.UniqueId.lower()) or
                   (c.WellName and search_lower in c.WellName.lower())
            ]
        
        if self.selected_reservoir:
            filtered = [c for c in filtered if c.Reservoir == self.selected_reservoir]
        
        self.completions = filtered
        self.available_unique_ids = [c.UniqueId for c in self.completions]

    def filter_completions(self, search_value: str):
        self.search_value = search_value
        self._apply_filters()

    def filter_by_reservoir(self, reservoir: str):
        self.selected_reservoir = reservoir if reservoir != "All Reservoirs" else ""
        self._apply_filters()

    def get_completion(self, completion: CompletionID):
        """Set current completion for editing."""
        self.current_completion = completion

    def update_completion(self, form_data: dict):
        """Update CompletionID Do and Dl fields in database."""
        try:
            if not self.current_completion:
                return rx.toast.error("No completion selected for update")
            
            unique_id = self.current_completion.UniqueId
            
            with rx.session() as session:
                completion_to_update = session.exec(
                    select(CompletionID).where(
                        CompletionID.UniqueId == unique_id
                    )
                ).first()
                
                if not completion_to_update:
                    return rx.toast.error(f"Completion '{unique_id}' not found")
                
                # Update Do (oil decline rate)
                do_value = form_data.get("Do")
                if do_value is not None and str(do_value).strip() != "":
                    try:
                        completion_to_update.Do = float(do_value)
                    except (ValueError, TypeError) as e:
                        print(f"Warning: Could not convert Do='{do_value}' to float: {e}")
                
                # Update Dl (liquid decline rate)
                dl_value = form_data.get("Dl")
                if dl_value is not None and str(dl_value).strip() != "":
                    try:
                        completion_to_update.Dl = float(dl_value)
                    except (ValueError, TypeError) as e:
                        print(f"Warning: Could not convert Dl='{dl_value}' to float: {e}")
                
                session.add(completion_to_update)
                session.commit()
                session.refresh(completion_to_update)
                self.current_completion = completion_to_update
            
            # Reload completions to reflect changes
            self._all_completions = []  # Clear cache to force reload
            self.load_completions()
            
            # Update selected completion if it was the one updated
            if self.selected_unique_id == unique_id:
                self.selected_completion = self.current_completion
                self.dio = self.current_completion.Do if self.current_completion.Do else 0.0
                self.dil = self.current_completion.Dl if self.current_completion.Dl else 0.0
            
            return rx.toast.success(f"Completion '{unique_id}' updated: Do={completion_to_update.Do}, Dl={completion_to_update.Dl}")
            
        except Exception as e:
            print(f"Update error: {e}")
            import traceback
            traceback.print_exc()
            return rx.toast.error(f"Failed to update completion: {str(e)}")

    def set_selected_unique_id(self, unique_id: str):
        """Set selected completion and trigger data load."""
        if unique_id == self.selected_unique_id:
            return
            
        self.selected_unique_id = unique_id
        self.forecast_data = []
        self.current_forecast_version = 0
        self.history_prod = []
        self.chart_data = []
        
        self.selected_completion = next(
            (c for c in self._all_completions if c.UniqueId == unique_id), 
            None
        )
        
        if self.selected_completion:
            self.dio = self.selected_completion.Do if self.selected_completion.Do else 0.0
            self.dil = self.selected_completion.Dl if self.selected_completion.Dl else 0.0
        
        return ProductionState.load_production_data_background

    async def load_production_data_background(self):
        """Load production data in background."""
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
                history_records = session.exec(
                    select(HistoryProd).where(
                        HistoryProd.UniqueId == unique_id,
                        HistoryProd.Date >= five_years_ago
                    ).order_by(desc(HistoryProd.Date))
                ).all()
                
                for rec in history_records:
                    oil_rate = rec.OilRate if rec.OilRate else 0.0
                    liq_rate = rec.LiqRate if rec.LiqRate else 0.0
                    wc = calculate_water_cut(oil_rate, liq_rate)
                    
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
                
                if self.available_forecast_versions:
                    self.current_forecast_version = max(self.available_forecast_versions)
                
                self.is_loading_production = False
            
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
        """Load forecast data for current version."""
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
                        "qOil": rec.Qoil,
                        "qLiq": rec.Qliq,
                        "wc": rec.WC
                    }
                    for rec in forecast_records
                ]
        except Exception as e:
            print(f"Error loading forecast: {e}")
            self.forecast_data = []

    def load_forecast_from_db(self):
        """Load forecast data synchronously."""
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
                        "qOil": rec.Qoil,
                        "qLiq": rec.Qliq,
                        "wc": rec.WC
                    }
                    for rec in forecast_records
                ]
        except Exception as e:
            print(f"Error loading forecast: {e}")
            self.forecast_data = []

    def set_forecast_version(self, version: int):
        self.current_forecast_version = version
        self.load_forecast_from_db()
        self._update_chart_data()

    def set_forecast_version_from_str(self, version_str: str):
        if version_str and version_str.startswith("v"):
            version = int(version_str[1:])
            self.set_forecast_version(version)

    def set_forecast_end_date(self, date: str):
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

    def _save_forecast_to_production_table(
        self, 
        unique_id: str, 
        forecast_points: list[ForecastPoint]
    ) -> int:
        """Save forecast to ProductionForecast table with FIFO version control."""
        try:
            with rx.session() as session:
                version = self._get_next_forecast_version(session, unique_id)
                created_at = datetime.now()
                
                for fp in forecast_points:
                    prod_record = ProductionForecast(
                        UniqueId=unique_id,
                        Date=fp.date,
                        Version=version,
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
            print(f"Error saving forecast: {e}")
            raise

    def _save_to_intervention_prod(
        self, 
        unique_id: str, 
        forecast_points: list[ForecastPoint]
    ):
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
                
                created_at = datetime.now()
                
                for fp in forecast_points:
                    intervention_record = InterventionForecast(
                        UniqueId=unique_id,
                        Date=fp.date,
                        Version=0,
                        DataType="Forecast",
                        OilRate=fp.oil_rate,
                        LiqRate=fp.liq_rate,
                        Qoil=fp.q_oil,
                        Qliq=fp.q_liq,
                        WC=fp.wc,
                        CreatedAt=created_at
                    )
                    session.add(intervention_record)
                
                session.commit()
                
        except Exception as e:
            print(f"Error saving to InterventionForecast: {e}")
            raise

    def run_forecast(self):
        """Run DCA forecast using elapsed days pattern.
        
        Formula: q(t) = qi * exp(-di * 12/365 * t)
        Where t is elapsed days from start date.
        
        Cumulative: Qoil = OilRate * K_oil * days_in_month
        """
        if not self.selected_completion or not self.forecast_end_date:
            return rx.toast.error("Please select a completion and set forecast end date")
        
        if self.qi_oil <= 0 and self.qi_liq <= 0:
            return rx.toast.error("No production history available")
        
        if self.dio <= 0:
            return rx.toast.error("Invalid decline rate (Di). Check CompletionID.Do value.")
        
        try:
            end_date = datetime.strptime(self.forecast_end_date, "%Y-%m-%d")
            
            # Get start date from last production record
            sorted_history = sorted(self.history_prod, key=lambda x: x["Date"])
            last_prod = sorted_history[-1]
            
            if isinstance(last_prod["Date"], datetime):
                start_date = last_prod["Date"]
            else:
                start_date = datetime.strptime(str(last_prod["Date"]), "%Y-%m-%d")
            
            if end_date <= start_date:
                return rx.toast.error(f"End date must be after {start_date.strftime('%Y-%m-%d')}")
            
            # Ensure KMonth data is loaded
            if not self.k_month_data:
                self.load_k_month_data()
            
            # Run DCA forecast using utility function
            forecast_points = run_dca_forecast(
                start_date=start_date,
                end_date=end_date,
                qi_oil=self.qi_oil,
                di_oil=self.dio,
                b_oil=self.b_oil,
                qi_liq=self.qi_liq,
                di_liq=self.dil,
                b_liq=self.b_liq,
                k_month_data=self.k_month_data,
                use_exponential=self.use_exponential_dca
            )
            
            if not forecast_points:
                return rx.toast.error("No forecast points generated. Check date range.")
            
            # Save to database
            version = self._save_forecast_to_production_table(self.selected_unique_id, forecast_points)
            
            # Save to InterventionProd if planned intervention exists
            if self.has_planned_intervention:
                self._save_to_intervention_prod(self.selected_unique_id, forecast_points)
            
            # Update state with forecast data
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
                forecast_versions = list(session.exec(
                    select(ProductionForecast.Version).where(
                        ProductionForecast.UniqueId == self.selected_unique_id
                    ).distinct()
                ).all())
                self.available_forecast_versions = sorted(forecast_versions)
            
            self._update_chart_data()
            
            # Calculate totals for message
            total_qoil = sum(fp.q_oil for fp in forecast_points)
            total_qliq = sum(fp.q_liq for fp in forecast_points)
            
            msg = f"Forecast v{version} saved: {len(forecast_points)} months, Qoil={total_qoil:.0f}t, Qliq={total_qliq:.0f}t"
            if self.has_planned_intervention:
                msg += " (+ InterventionForecast v0)"
            
            return rx.toast.success(msg)
            
        except Exception as e:
            print(f"Forecast error: {e}")
            import traceback
            traceback.print_exc()
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
            {
                "Date": f["date"], 
                "OilRate": f"{f['oilRate']:.1f}", 
                "LiqRate": f"{f['liqRate']:.1f}", 
                "WC": f"{f['wc']:.1f}",
                "WC_val": f['wc'],
                "Qoil": f"{f['qOil']:.0f}",
                "Qliq": f"{f['qLiq']:.0f}"
            }
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
    def forecast_totals_display(self) -> str:
        """Display total cumulative production from forecast."""
        if not self.forecast_data:
            return "No forecast"
        total_qoil = sum(f["qOil"] for f in self.forecast_data)
        total_qliq = sum(f["qLiq"] for f in self.forecast_data)
        return f"Total: Qoil={total_qoil:.0f}t | Qliq={total_qliq:.0f}t"
    
    @rx.var
    def k_month_loaded(self) -> bool:
        """Check if KMonth data is loaded."""
        return len(self.k_month_data) > 0