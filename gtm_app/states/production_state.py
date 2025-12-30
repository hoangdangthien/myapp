"""Updated Production State with Intervention-aware Forecast Logic.

This state manages Production monitoring and forecasting with:
- Dip: Platform-level decline adjustment
- Dir: Reservoir+Field level decline adjustment
- Intervention detection and handling

Forecast Logic:
1. No intervention in current year → Standard exponential DCA
2. One Done intervention → Use intervention parameters
3. One Plan intervention → Base forecast + replace after intervention date
4. Multiple interventions → Use last intervention, replace after first Plan date

DCA Formula: q(t) = qi * exp(-Di_eff * 12/365 * t)
Effective Decline: Di_eff = Do * (1 + Dip) * (1 + Dir)
"""
import reflex as rx
from typing import Optional, List, Tuple, Dict
from datetime import datetime, timedelta
from sqlmodel import select, delete, func, desc, or_
import numpy as np

from ..models import (
    CompletionID,
    HistoryProd,
    ProductionForecast,
    InterventionID,
    InterventionForecast,
    WellID,
    MAX_PRODUCTION_FORECAST_VERSIONS,
    FIELD_OPTIONS,
    RESERVOIR_OPTIONS,
)
from ..services.dca_service import DCAService, ForecastConfig, ForecastResult
from ..services.database_service import DatabaseService
from .shared_state import SharedForecastState
from ..utils.dca_utils import (
    arps_exponential,
    arps_decline,
    generate_forecast_dates,
    calculate_water_cut,
    ForecastPoint,
)


class ProductionState(SharedForecastState):
    """State for Production monitoring and forecasting with intervention-aware logic."""
    
    # CompletionID data
    completions: List[CompletionID] = []
    _all_completions: List[CompletionID] = []
    
    selected_completion: Optional[CompletionID] = None
    selected_id: str = ""
    available_ids: List[str] = []
    current_completion: Optional[CompletionID] = None
    
    # DCA parameters from CompletionID
    qi_oil: float = 0.0
    qi_liq: float = 0.0
    dio: float = 0.0
    dil: float = 0.0
    b_oil: float = 0.0
    b_liq: float = 0.0
    
    # Decline adjustment parameters
    dip: float = 0.0
    dir: float = 0.0
    
    # Intervention status for selected completion
    has_planned_intervention: bool = False
    has_done_intervention: bool = False
    intervention_info: str = ""
    interventions_this_year: List[InterventionID] = []
    
    # Search/filter
    search_value: str = ""
    selected_reservoir: str = ""
    
    # Loading states
    is_loading_completions: bool = False
    is_loading_production: bool = False
    
    # Batch Forecast State
    is_batch_forecasting: bool = False
    batch_forecast_progress: int = 0
    batch_forecast_total: int = 0
    batch_forecast_current: str = ""
    batch_forecast_results: List[dict] = []
    batch_forecast_errors: List[str] = []
    batch_forecast_cancelled: bool = False

    # ========== Load Methods ==========

    def load_completions(self):
        """Load all completions from CompletionID table."""
        try:
            self.is_loading_completions = True
            self._load_k_month_data()
            
            with rx.session() as session:
                self._all_completions = session.exec(select(CompletionID)).all()
            
            self._apply_filters()
            
            if self.available_ids and not self.selected_id:
                self.selected_id = self.available_ids[0]
                
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
        self.available_ids = [c.UniqueId for c in self.completions]

    def filter_completions(self, search_value: str):
        """Filter completions by search term."""
        self.search_value = search_value
        self._apply_filters()

    def clear_filters(self):
        """Clear all filters."""
        self.search_value = ""
        self.selected_reservoir = ""
        self._apply_filters()

    def get_completion(self, completion: CompletionID):
        """Set current completion for editing."""
        self.current_completion = completion

    def update_completion(self, form_data: dict):
        """Update CompletionID Do, Dl, Dip, Dir fields in database."""
        try:
            if not self.current_completion:
                return rx.toast.error("No completion selected for update")
            
            unique_id = self.current_completion.UniqueId
            
            with rx.session() as session:
                completion_to_update = session.exec(
                    select(CompletionID).where(CompletionID.UniqueId == unique_id)
                ).first()
                
                if not completion_to_update:
                    return rx.toast.error(f"Completion '{unique_id}' not found")
                
                for field in ["Do", "Dl", "Dip", "Dir"]:
                    value = form_data.get(field)
                    if value is not None and str(value).strip() != "":
                        try:
                            setattr(completion_to_update, field, float(value))
                        except (ValueError, TypeError) as e:
                            print(f"Warning: Could not convert {field}='{value}' to float: {e}")
                
                session.add(completion_to_update)
                session.commit()
                session.refresh(completion_to_update)
                self.current_completion = completion_to_update
            
            self._all_completions = []
            self.load_completions()
            
            if self.selected_id == unique_id:
                self.selected_completion = self.current_completion
                self.dio = self.current_completion.Do if self.current_completion.Do else 0.0
                self.dil = self.current_completion.Dl if self.current_completion.Dl else 0.0
                self.dip = self.current_completion.Dip if self.current_completion.Dip else 0.0
                self.dir = self.current_completion.Dir if self.current_completion.Dir else 0.0
            
            return rx.toast.success(f"Completion '{unique_id}' updated")
            
        except Exception as e:
            print(f"Update error: {e}")
            return rx.toast.error(f"Failed to update completion: {str(e)}")

    def batch_update_dip(self, form_data: dict):
        """Batch update Dip for all completions on a platform."""
        try:
            platform = form_data.get("platform")
            dip_value = float(form_data.get("dip_value", 0))
            
            if not platform:
                return rx.toast.error("Please select a platform")
            
            updated_count = 0
            with rx.session() as session:
                completions = session.exec(
                    select(CompletionID).join(
                        WellID, CompletionID.WellName == WellID.WellName
                    ).where(WellID.Platform == platform)
                ).all()
                
                for comp in completions:
                    comp.Dip = dip_value
                    session.add(comp)
                    updated_count += 1
                
                session.commit()
            
            self._all_completions = []
            self.load_completions()
            
            return rx.toast.success(f"Updated Dip={dip_value} for {updated_count} completions on {platform}")
            
        except Exception as e:
            return rx.toast.error(f"Batch update failed: {str(e)}")

    def batch_update_dir(self, form_data: dict):
        """Batch update Dir for all completions in a reservoir+field."""
        try:
            field = form_data.get("field")
            reservoir = form_data.get("reservoir")
            dir_value = float(form_data.get("dir_value", 0))
            
            if not field or not reservoir:
                return rx.toast.error("Please select both field and reservoir")
            
            updated_count = 0
            with rx.session() as session:
                completions = session.exec(
                    select(CompletionID).join(
                        WellID, CompletionID.WellName == WellID.WellName
                    ).where(
                        WellID.Field == field,
                        CompletionID.Reservoir == reservoir
                    )
                ).all()
                
                for comp in completions:
                    comp.Dir = dir_value
                    session.add(comp)
                    updated_count += 1
                
                session.commit()
            
            self._all_completions = []
            self.load_completions()
            
            return rx.toast.success(
                f"Updated Dir={dir_value} for {updated_count} completions in {reservoir} of {field}"
            )
            
        except Exception as e:
            return rx.toast.error(f"Batch update failed: {str(e)}")

    def set_selected_id(self, unique_id: str):
        """Set selected completion and trigger data load."""
        if unique_id == self.selected_id:
            return
            
        self.selected_id = unique_id
        self.forecast_data = []
        self.current_forecast_version = 0
        self.history_prod = []
        self.chart_data = []
        self.interventions_this_year = []
        
        self.selected_completion = next(
            (c for c in self._all_completions if c.UniqueId == unique_id), 
            None
        )
        
        if self.selected_completion:
            self.dio = self.selected_completion.Do if self.selected_completion.Do else 0.0
            self.dil = self.selected_completion.Dl if self.selected_completion.Dl else 0.0
            self.dip = self.selected_completion.Dip if self.selected_completion.Dip else 0.0
            self.dir = self.selected_completion.Dir if self.selected_completion.Dir else 0.0
        
        return ProductionState.load_production_data_background

    @rx.event(background=True)
    async def load_production_data_background(self):
        """Load production data in background."""
        async with self:
            self.is_loading_production = True
        
        try:
            unique_id = None
            async with self:
                unique_id = self.selected_id
            
            if not unique_id:
                return
            
            history_data = []
            forecast_versions = []
            interventions_current_year = []
            current_year = datetime.now().year
            
            with rx.session() as session:
                # Load history data
                history_data = DCAService.load_history_data(session, unique_id, years=5)
                
                # Load interventions for this UniqueId in current year
                interventions_current_year = session.exec(
                    select(InterventionID).where(
                        InterventionID.UniqueId == unique_id,
                        InterventionID.InterventionYear == current_year
                    ).order_by(InterventionID.PlanningDate)
                ).all()
                
                # Get forecast versions
                forecast_versions = DatabaseService.get_available_versions(
                    session, ProductionForecast, unique_id, min_version=1
                )
            
            # Analyze interventions
            has_plan = any(i.Status == "Plan" for i in interventions_current_year)
            has_done = any(i.Status == "Done" for i in interventions_current_year)
            
            # Build intervention info string
            intervention_text = ""
            if interventions_current_year:
                plan_count = sum(1 for i in interventions_current_year if i.Status == "Plan")
                done_count = sum(1 for i in interventions_current_year if i.Status == "Done")
                intervention_text = f"{done_count} Done, {plan_count} Plan in {current_year}"
            
            async with self:
                self.history_prod = history_data
                self.has_planned_intervention = has_plan
                self.has_done_intervention = has_done
                self.intervention_info = intervention_text
                self.interventions_this_year = interventions_current_year
                self.available_forecast_versions = forecast_versions
                
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
                    self._load_forecast_from_db()
                self._update_chart_data()
                
        except Exception as e:
            print(f"Error loading production data: {e}")
            async with self:
                self.history_prod = []
                self.is_loading_production = False

    def _load_forecast_from_db(self):
        """Load forecast data for current version from database."""
        if not self.selected_id or self.current_forecast_version == 0:
            self.forecast_data = []
            return
        
        try:
            with rx.session() as session:
                self.forecast_data = DatabaseService.load_forecast_by_version(
                    session, ProductionForecast, self.selected_id, self.current_forecast_version
                )
        except Exception as e:
            print(f"Error loading forecast: {e}")
            self.forecast_data = []

    def load_forecast_from_db(self):
        """Public method to load forecast data synchronously."""
        self._load_forecast_from_db()

    def set_forecast_version(self, version: int):
        """Set and load a specific forecast version."""
        self.current_forecast_version = version
        self.load_forecast_from_db()
        self._update_chart_data()

    def set_forecast_version_from_str(self, version_str: str):
        """Set forecast version from string (e.g., "v1")."""
        if version_str and version_str.startswith("v"):
            version = int(version_str[1:])
            self.set_forecast_version(version)

    # ========== Intervention-Aware Forecast Logic ==========

    def _get_interventions_for_completion(self, session, unique_id: str, year: int) -> List[InterventionID]:
        """Get all interventions for a completion in a specific year."""
        return session.exec(
            select(InterventionID).where(
                InterventionID.UniqueId == unique_id,
                InterventionID.InterventionYear == year
            ).order_by(InterventionID.PlanningDate)
        ).all()

    def _run_exponential_forecast(
        self,
        start_date: datetime,
        end_date: datetime,
        qi_oil: float,
        qi_liq: float,
        di_oil_eff: float,
        di_liq_eff: float
    ) -> List[ForecastPoint]:
        """Run standard exponential DCA forecast."""
        date_range, elapsed_days, days_in_month, month_indices = generate_forecast_dates(
            start_date, end_date
        )
        
        if len(date_range) == 0:
            return []
        
        # Get K factors
        k_oil_array = np.array([
            self.k_month_data.get(m, {}).get("K_oil", 1.0) 
            for m in month_indices
        ])
        k_liq_array = np.array([
            self.k_month_data.get(m, {}).get("K_liq", 1.0) 
            for m in month_indices
        ])
        
        # Calculate rates using exponential decline
        oil_rates = arps_exponential(qi_oil, di_oil_eff, elapsed_days)
        liq_rates = arps_exponential(qi_liq, di_liq_eff, elapsed_days)
        
        # Ensure non-negative
        oil_rates = np.maximum(0.0, oil_rates)
        liq_rates = np.maximum(0.0, liq_rates)
        
        # Calculate cumulative
        q_oil_array = oil_rates * k_oil_array * days_in_month
        q_liq_array = liq_rates * k_liq_array * days_in_month
        
        forecast_points = []
        for i, date in enumerate(date_range):
            wc = calculate_water_cut(oil_rates[i], liq_rates[i])
            forecast_points.append(ForecastPoint(
                date=date.to_pydatetime() if hasattr(date, 'to_pydatetime') else date,
                days_in_month=int(days_in_month[i]),
                oil_rate=round(float(oil_rates[i]), 2),
                liq_rate=round(float(liq_rates[i]), 2),
                q_oil=round(float(q_oil_array[i]), 2),
                q_liq=round(float(q_liq_array[i]), 2),
                wc=round(wc, 2)
            ))
        
        return forecast_points

    def _run_intervention_forecast(
        self,
        intervention: InterventionID,
        start_date: datetime,
        end_date: datetime,
        last_actual_oil: float = None,
        last_actual_liq: float = None
    ) -> List[ForecastPoint]:
        """Run hyperbolic DCA forecast using intervention parameters."""
        qi_oil = intervention.InitialORate if intervention.InitialORate else 0.0
        b_oil = intervention.bo if intervention.bo else 0.0
        di_oil = intervention.Dio if intervention.Dio else 0.0
        qi_liq = intervention.InitialLRate if intervention.InitialLRate else 0.0
        b_liq = intervention.bl if intervention.bl else 0.0
        di_liq = intervention.Dil if intervention.Dil else 0.0
        
        date_range, elapsed_days, days_in_month, month_indices = generate_forecast_dates(
            start_date, end_date
        )
        
        if len(date_range) == 0:
            return []
        
        # Get K_int factors
        k_int_array = np.array([
            self.k_month_data.get(m, {}).get("K_int", 1.0) 
            for m in month_indices
        ])
        
        # Calculate rates using Arps decline (hyperbolic if b > 0)
        oil_rates = arps_decline(qi_oil, di_oil, b_oil, elapsed_days)
        liq_rates = arps_decline(qi_liq, di_liq, b_liq, elapsed_days)
        
        # Apply ratio adjustment if actual rates provided
        ratio_oil = 1.0
        ratio_liq = 1.0
        if last_actual_oil is not None and oil_rates[0] > 0:
            ratio_oil = last_actual_oil / oil_rates[0]
        if last_actual_liq is not None and liq_rates[0] > 0:
            ratio_liq = last_actual_liq / liq_rates[0]
        
        oil_rates = oil_rates * ratio_oil
        liq_rates = liq_rates * ratio_liq
        
        # Ensure non-negative
        oil_rates = np.maximum(0.0, oil_rates)
        liq_rates = np.maximum(0.0, liq_rates)
        
        # Calculate cumulative using K_int
        q_oil_array = oil_rates * k_int_array * days_in_month
        q_liq_array = liq_rates * k_int_array * days_in_month
        
        forecast_points = []
        for i, date in enumerate(date_range):
            wc = calculate_water_cut(oil_rates[i], liq_rates[i])
            forecast_points.append(ForecastPoint(
                date=date.to_pydatetime() if hasattr(date, 'to_pydatetime') else date,
                days_in_month=int(days_in_month[i]),
                oil_rate=round(float(oil_rates[i]), 2),
                liq_rate=round(float(liq_rates[i]), 2),
                q_oil=round(float(q_oil_array[i]), 2),
                q_liq=round(float(q_liq_array[i]), 2),
                wc=round(wc, 2)
            ))
        
        return forecast_points

    def _merge_forecasts(
        self,
        base_forecast: List[ForecastPoint],
        intervention_forecast: List[ForecastPoint],
        intervention_date: datetime
    ) -> List[ForecastPoint]:
        """Merge base forecast with intervention forecast.
        
        Returns base forecast values before intervention date,
        and intervention forecast values from intervention date onwards.
        """
        merged = []
        
        # Convert intervention_date to date only for comparison
        intv_date = intervention_date.date() if isinstance(intervention_date, datetime) else intervention_date
        
        # Add base forecast points before intervention date
        for fp in base_forecast:
            fp_date = fp.date.date() if isinstance(fp.date, datetime) else fp.date
            if fp_date < intv_date:
                merged.append(fp)
        
        # Add intervention forecast points from intervention date onwards
        for fp in intervention_forecast:
            fp_date = fp.date.date() if isinstance(fp.date, datetime) else fp.date
            if fp_date >= intv_date:
                merged.append(fp)
        
        # Sort by date
        merged.sort(key=lambda x: x.date)
        
        return merged

    def _save_to_intervention_forecast(
        self,
        session,
        intervention: InterventionID,
        forecast_points: List[ForecastPoint],
        version: int
    ):
        """Save forecast to InterventionForecast table."""
        created_at = datetime.now()
        
        # Delete existing records for this version
        session.exec(
            delete(InterventionForecast).where(
                InterventionForecast.ID == intervention.ID,
                InterventionForecast.Version == version
            )
        )
        session.commit()
        
        for fp in forecast_points:
            record = InterventionForecast(
                ID=intervention.ID,
                UniqueId=intervention.UniqueId,
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

    def run_forecast(self):
        """Run DCA forecast with intervention-aware logic.
        
        Logic:
        1. No intervention in current year → Standard exponential DCA
        2. One Done intervention only → Use intervention parameters
        3. One Plan intervention only → 
           - Create base forecast (exponential) → save to InterventionForecast v0
           - Replace values after intervention date with intervention forecast → save to ProductionForecast
        4. Multiple interventions (Done + Plan) →
           - Use last intervention parameters
           - Save to InterventionForecast as base for next Plan
           - Replace values after first Plan intervention date → save to ProductionForecast
        """
        if not self.selected_completion or not self.forecast_end_date:
            return rx.toast.error("Please select a completion and set forecast end date")
        
        if self.qi_oil <= 0 and self.qi_liq <= 0:
            return rx.toast.error("No production history available")
        
        if self.dio <= 0:
            return rx.toast.error("Invalid decline rate (Di). Check CompletionID.Do value.")
        
        try:
            end_date = datetime.strptime(self.forecast_end_date, "%Y-%m-%d")
            current_year = datetime.now().year
            
            # Get last production record
            sorted_history = sorted(self.history_prod, key=lambda x: x["Date"])
            last_prod = sorted_history[-1]
            
            if isinstance(last_prod["Date"], datetime):
                start_date = last_prod["Date"]
            else:
                start_date = datetime.strptime(str(last_prod["Date"]), "%Y-%m-%d")
            
            if end_date <= start_date:
                return rx.toast.error(f"End date must be after {start_date.strftime('%Y-%m-%d')}")
            
            self._load_k_month_data()
            
            # Calculate effective decline rates
            di_oil_eff = self.dio * (1 + self.dip) * (1 + self.dir)
            di_liq_eff = (self.dil if self.dil > 0 else self.dio) * (1 + self.dip) * (1 + self.dir)
            
            # Get interventions for current year
            with rx.session() as session:
                interventions = self._get_interventions_for_completion(
                    session, self.selected_id, current_year
                )
            
            # Separate by status
            done_interventions = [i for i in interventions if i.Status == "Done"]
            plan_interventions = [i for i in interventions if i.Status == "Plan"]
            
            final_forecast_points = []
            message_parts = []
            
            # ========== CASE 1: No intervention in current year ==========
            if not interventions:
                final_forecast_points = self._run_exponential_forecast(
                    start_date=start_date,
                    end_date=end_date,
                    qi_oil=self.qi_oil,
                    qi_liq=self.qi_liq,
                    di_oil_eff=di_oil_eff,
                    di_liq_eff=di_liq_eff
                )
                message_parts.append("Standard exponential DCA (no intervention)")
            
            # ========== CASE 2: Only Done interventions ==========
            elif done_interventions and not plan_interventions:
                # Use the last Done intervention parameters
                last_done = done_interventions[-1]
                
                final_forecast_points = self._run_intervention_forecast(
                    intervention=last_done,
                    start_date=start_date,
                    end_date=end_date,
                    last_actual_oil=self.qi_oil,
                    last_actual_liq=self.qi_liq
                )
                message_parts.append(f"Using Done intervention ({last_done.TypeGTM}) parameters")
            
            # ========== CASE 3: Only Plan intervention ==========
            elif plan_interventions and not done_interventions:
                first_plan = plan_interventions[0]
                plan_date = datetime.strptime(first_plan.PlanningDate[:10], "%Y-%m-%d")
                
                # Step 1: Create base forecast (exponential from last rate to end date)
                base_forecast = self._run_exponential_forecast(
                    start_date=start_date,
                    end_date=end_date,
                    qi_oil=self.qi_oil,
                    qi_liq=self.qi_liq,
                    di_oil_eff=di_oil_eff,
                    di_liq_eff=di_liq_eff
                )
                
                # Save base forecast to InterventionForecast v0
                with rx.session() as session:
                    self._save_to_intervention_forecast(
                        session, first_plan, base_forecast, version=0
                    )
                message_parts.append("Base forecast saved to InterventionForecast v0")
                
                # Step 2: Create intervention forecast from planning date
                intervention_forecast = self._run_intervention_forecast(
                    intervention=first_plan,
                    start_date=plan_date,
                    end_date=end_date
                )
                
                # Step 3: Merge - use base before intervention date, intervention after
                final_forecast_points = self._merge_forecasts(
                    base_forecast=base_forecast,
                    intervention_forecast=intervention_forecast,
                    intervention_date=plan_date
                )
                message_parts.append(f"Merged with Plan intervention ({first_plan.TypeGTM}) from {first_plan.PlanningDate}")
            
            # ========== CASE 4: Both Done and Plan interventions ==========
            else:
                # Use last intervention (could be Done or Plan based on date)
                all_sorted = sorted(interventions, key=lambda x: x.PlanningDate)
                last_intervention = all_sorted[-1]
                first_plan = plan_interventions[0] if plan_interventions else None
                
                # Create forecast using last intervention parameters
                last_intv_date = datetime.strptime(last_intervention.PlanningDate[:10], "%Y-%m-%d")
                
                # If last is Done, start from last history date
                # If last is Plan, we need to handle it differently
                if last_intervention.Status == "Done":
                    base_start = start_date
                else:
                    base_start = last_intv_date
                
                # Create base forecast using exponential from last rate
                base_forecast = self._run_exponential_forecast(
                    start_date=start_date,
                    end_date=end_date,
                    qi_oil=self.qi_oil,
                    qi_liq=self.qi_liq,
                    di_oil_eff=di_oil_eff,
                    di_liq_eff=di_liq_eff
                )
                
                # Save to InterventionForecast as base for next Plan
                if first_plan:
                    with rx.session() as session:
                        self._save_to_intervention_forecast(
                            session, first_plan, base_forecast, version=0
                        )
                    message_parts.append(f"Base saved for Plan intervention ({first_plan.TypeGTM})")
                
                # Create intervention forecast from first Plan date
                if first_plan:
                    first_plan_date = datetime.strptime(first_plan.PlanningDate[:10], "%Y-%m-%d")
                    
                    intervention_forecast = self._run_intervention_forecast(
                        intervention=first_plan,
                        start_date=first_plan_date,
                        end_date=end_date
                    )
                    
                    # Merge forecasts
                    final_forecast_points = self._merge_forecasts(
                        base_forecast=base_forecast,
                        intervention_forecast=intervention_forecast,
                        intervention_date=first_plan_date
                    )
                    message_parts.append(f"Merged at Plan date ({first_plan.PlanningDate})")
                else:
                    # Only Done interventions, use intervention forecast
                    final_forecast_points = self._run_intervention_forecast(
                        intervention=last_intervention,
                        start_date=start_date,
                        end_date=end_date,
                        last_actual_oil=self.qi_oil,
                        last_actual_liq=self.qi_liq
                    )
                    message_parts.append(f"Using last Done intervention ({last_intervention.TypeGTM})")
            
            if not final_forecast_points:
                return rx.toast.error("Forecast failed - no data generated")
            
            # Save to ProductionForecast
            with rx.session() as session:
                version = DCAService.get_next_version_fifo(
                    session, ProductionForecast, self.selected_id,
                    MAX_PRODUCTION_FORECAST_VERSIONS, min_version=1
                )
                DCAService.save_forecast(
                    session, ProductionForecast, self.selected_id,
                    final_forecast_points, version
                )
            
            # Update state
            self.forecast_data = DCAService.forecast_to_dict_list(final_forecast_points)
            self.current_forecast_version = version
            
            with rx.session() as session:
                self.available_forecast_versions = DatabaseService.get_available_versions(
                    session, ProductionForecast, self.selected_id, min_version=1
                )
            
            self._update_chart_data()
            
            # Calculate totals
            total_qoil = sum(fp.q_oil for fp in final_forecast_points)
            total_qliq = sum(fp.q_liq for fp in final_forecast_points)
            
            msg = f"Forecast v{version}: {len(final_forecast_points)} months, Qoil={total_qoil:.0f}t. {'; '.join(message_parts)}"
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
                        ProductionForecast.UniqueId == self.selected_id,
                        ProductionForecast.Version == version
                    )
                )
                session.commit()
                
                self.available_forecast_versions = DatabaseService.get_available_versions(
                    session, ProductionForecast, self.selected_id, min_version=1
                )
            
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
        """Delete the currently selected forecast version."""
        return self.delete_forecast_version(self.current_forecast_version)

    # ========== Batch Forecast ==========

    def cancel_batch_forecast(self):
        """Cancel the running batch forecast."""
        self.batch_forecast_cancelled = True
        return rx.toast.warning("Batch forecast cancellation requested...")

    def run_forecast_all(self):
        """Run DCA forecast for all completions with intervention-aware logic."""
        if not self.forecast_end_date:
            yield rx.toast.error("Please set forecast end date first")
            return
            
        if not self._all_completions:
            yield rx.toast.error("No completions loaded")
            return
        
        self.is_batch_forecasting = True
        self.batch_forecast_cancelled = False
        self.batch_forecast_progress = 0
        self.batch_forecast_total = len(self.completions)
        self.batch_forecast_results = []
        self.batch_forecast_errors = []
        self.batch_forecast_current = "Initializing..."
        
        yield rx.toast.info(f"Starting batch forecast for {self.batch_forecast_total} completions...")
        
        try:
            end_date = datetime.strptime(self.forecast_end_date, "%Y-%m-%d")
            five_years_ago = datetime.now() - timedelta(days=5*365)
            current_year = datetime.now().year
            
            self._load_k_month_data()
            
            # Pre-load data
            with rx.session() as session:
                history_by_completion = DatabaseService.bulk_load_history(
                    session, HistoryProd, cutoff_date=five_years_ago
                )
                
                # Load all interventions for current year
                all_interventions = session.exec(
                    select(InterventionID).where(
                        InterventionID.InterventionYear == current_year
                    )
                ).all()
                
                # Group by UniqueId
                interventions_by_uid: Dict[str, List[InterventionID]] = {}
                for intv in all_interventions:
                    if intv.UniqueId not in interventions_by_uid:
                        interventions_by_uid[intv.UniqueId] = []
                    interventions_by_uid[intv.UniqueId].append(intv)
            
            success_count = 0
            error_count = 0
            total_qoil = 0.0
            total_qliq = 0.0
            
            for i, completion in enumerate(self.completions):
                if self.batch_forecast_cancelled:
                    break
                
                self.batch_forecast_progress = i + 1
                self.batch_forecast_current = f"Processing: {completion.UniqueId}"
                
                unique_id = completion.UniqueId
                history = history_by_completion.get(unique_id, [])
                
                if not history:
                    self.batch_forecast_errors.append(f"{unique_id}: No history data")
                    error_count += 1
                    continue
                
                di_oil = completion.Do if completion.Do and completion.Do > 0 else 0.0
                
                if di_oil <= 0:
                    self.batch_forecast_errors.append(f"{unique_id}: Invalid Di")
                    error_count += 1
                    continue
                
                sorted_history = sorted(history, key=lambda x: x["Date"])
                last_prod = sorted_history[-1]
                
                start_date = last_prod["Date"]
                if isinstance(start_date, str):
                    start_date = datetime.strptime(start_date, "%Y-%m-%d")
                
                qi_oil = last_prod["OilRate"]
                qi_liq = last_prod["LiqRate"]
                
                # Get adjustments
                dip = completion.Dip if completion.Dip else 0.0
                dir_val = completion.Dir if completion.Dir else 0.0
                di_liq = completion.Dl if completion.Dl and completion.Dl > 0 else di_oil
                
                di_oil_eff = di_oil * (1 + dip) * (1 + dir_val)
                di_liq_eff = di_liq * (1 + dip) * (1 + dir_val)
                
                # Get interventions for this completion
                interventions = interventions_by_uid.get(unique_id, [])
                done_interventions = [i for i in interventions if i.Status == "Done"]
                plan_interventions = [i for i in interventions if i.Status == "Plan"]
                
                try:
                    forecast_points = []
                    forecast_type = ""
                    
                    # Apply same logic as single forecast
                    if not interventions:
                        # No intervention - standard exponential
                        forecast_points = self._run_exponential_forecast(
                            start_date, end_date, qi_oil, qi_liq, di_oil_eff, di_liq_eff
                        )
                        forecast_type = "Exponential"
                    
                    elif done_interventions and not plan_interventions:
                        # Only Done - use last Done params
                        last_done = done_interventions[-1]
                        forecast_points = self._run_intervention_forecast(
                            last_done, start_date, end_date, qi_oil, qi_liq
                        )
                        forecast_type = f"Done ({last_done.TypeGTM})"
                    
                    elif plan_interventions and not done_interventions:
                        # Only Plan - base + merge
                        first_plan = plan_interventions[0]
                        plan_date = datetime.strptime(first_plan.PlanningDate[:10], "%Y-%m-%d")
                        
                        base_forecast = self._run_exponential_forecast(
                            start_date, end_date, qi_oil, qi_liq, di_oil_eff, di_liq_eff
                        )
                        
                        # Save base to InterventionForecast v0
                        with rx.session() as session:
                            self._save_to_intervention_forecast(session, first_plan, base_forecast, 0)
                        
                        intv_forecast = self._run_intervention_forecast(
                            first_plan, plan_date, end_date
                        )
                        
                        forecast_points = self._merge_forecasts(base_forecast, intv_forecast, plan_date)
                        forecast_type = f"Plan ({first_plan.TypeGTM})"
                    
                    else:
                        # Both Done and Plan
                        first_plan = plan_interventions[0] if plan_interventions else None
                        
                        base_forecast = self._run_exponential_forecast(
                            start_date, end_date, qi_oil, qi_liq, di_oil_eff, di_liq_eff
                        )
                        
                        if first_plan:
                            with rx.session() as session:
                                self._save_to_intervention_forecast(session, first_plan, base_forecast, 0)
                            
                            plan_date = datetime.strptime(first_plan.PlanningDate[:10], "%Y-%m-%d")
                            intv_forecast = self._run_intervention_forecast(first_plan, plan_date, end_date)
                            forecast_points = self._merge_forecasts(base_forecast, intv_forecast, plan_date)
                            forecast_type = f"Mixed ({len(done_interventions)}D+{len(plan_interventions)}P)"
                        else:
                            last_done = done_interventions[-1]
                            forecast_points = self._run_intervention_forecast(
                                last_done, start_date, end_date, qi_oil, qi_liq
                            )
                            forecast_type = f"Done ({last_done.TypeGTM})"
                    
                    if not forecast_points:
                        self.batch_forecast_errors.append(f"{unique_id}: No forecast generated")
                        error_count += 1
                        continue
                    
                    # Calculate totals
                    qoil = sum(fp.q_oil for fp in forecast_points)
                    qliq = sum(fp.q_liq for fp in forecast_points)
                    total_qoil += qoil
                    total_qliq += qliq
                    
                    # Save to ProductionForecast
                    with rx.session() as session:
                        version = DCAService.get_next_version_fifo(
                            session, ProductionForecast, unique_id,
                            MAX_PRODUCTION_FORECAST_VERSIONS, min_version=1
                        )
                        DCAService.save_forecast(
                            session, ProductionForecast, unique_id,
                            forecast_points, version
                        )
                    
                    success_count += 1
                    self.batch_forecast_results.append({
                        "UniqueId": unique_id,
                        "Version": version,
                        "Months": len(forecast_points),
                        "Qoil": round(qoil, 0),
                        "Qliq": round(qliq, 0),
                        "Type": forecast_type,
                        "Di_eff": round(di_oil_eff, 4)
                    })
                    
                except Exception as e:
                    self.batch_forecast_errors.append(f"{unique_id}: {str(e)}")
                    error_count += 1
            
            self.is_batch_forecasting = False
            self.batch_forecast_current = "Complete"
            
            if self.batch_forecast_cancelled:
                yield rx.toast.warning(
                    f"Batch cancelled. Processed {success_count}/{len(self.completions)}"
                )
            else:
                yield rx.toast.success(
                    f"Batch complete: {success_count} success, {error_count} errors. "
                    f"Total Qoil={total_qoil:.0f}t"
                )
            
        except Exception as e:
            print(f"Batch forecast error: {e}")
            self.is_batch_forecasting = False
            yield rx.toast.error(f"Batch forecast failed: {str(e)}")

    # ========== Computed Properties ==========
    
    @rx.var
    def total_completions(self) -> int:
        return len(self.completions)
    
    @rx.var
    def unique_reservoirs(self) -> List[str]:
        reservoirs = set(c.Reservoir for c in self._all_completions if c.Reservoir)
        return ["All Reservoirs"] + sorted(reservoirs)
    
    @rx.var
    def unique_platforms(self) -> List[str]:
        from ..models import PLATFORM_OPTIONS
        return PLATFORM_OPTIONS
    
    @rx.var
    def unique_fields(self) -> List[str]:
        return FIELD_OPTIONS
    
    @rx.var
    def dca_parameters_display(self) -> str:
        return f"Do: {self.dio:.4f} | Dl: {self.dil:.4f}"
    
    @rx.var
    def dip_display(self) -> str:
        return f"{self.dip:.2f}"
    
    @rx.var
    def dir_display(self) -> str:
        return f"{self.dir:.2f}"
    
    @rx.var
    def effective_di_oil(self) -> float:
        return self.dio * (1 + self.dip) * (1 + self.dir)
    
    @rx.var
    def effective_di_display(self) -> str:
        return f"{self.effective_di_oil:.4f}"
    
    @rx.var
    def production_table_data(self) -> List[dict]:
        return self._format_history_for_table(24)
    
    @rx.var
    def forecast_table_data(self) -> List[dict]:
        return self._format_forecast_for_table(24)
    
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
    def intervention_status_display(self) -> str:
        """Display intervention status for selected completion."""
        if not self.interventions_this_year:
            return "No intervention this year"
        return self.intervention_info
    
    @rx.var
    def batch_progress_percent(self) -> int:
        if self.batch_forecast_total == 0:
            return 0
        return int((self.batch_forecast_progress / self.batch_forecast_total) * 100)
    
    @rx.var
    def batch_progress_display(self) -> str:
        return f"{self.batch_forecast_progress}/{self.batch_forecast_total}"
    
    @rx.var
    def batch_success_count(self) -> int:
        return len(self.batch_forecast_results)
    
    @rx.var
    def batch_error_count(self) -> int:
        return len(self.batch_forecast_errors)
    
    @rx.var
    def batch_total_qoil(self) -> float:
        return sum(r.get("Qoil", 0) for r in self.batch_forecast_results)
    
    @rx.var
    def batch_total_qliq(self) -> float:
        return sum(r.get("Qliq", 0) for r in self.batch_forecast_results)
    
    @rx.var
    def batch_total_qoil_display(self) -> str:
        return f"{int(self.batch_total_qoil)}"
    
    @rx.var
    def batch_total_qliq_display(self) -> str:
        return f"{int(self.batch_total_qliq)}"
    
    @rx.var
    def batch_errors_display(self) -> List[str]:
        return self.batch_forecast_errors[:10]