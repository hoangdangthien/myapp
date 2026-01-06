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
import pandas as pd

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
from ..services.production_forecast_service import ProductionForecastService
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

    #page pagination
    completion_page_size: int = 20
    completion_offset: int = 0
    completion_total_count: int = 0

    # ========== Load Methods ==========

    def load_completions(self):
        '''Load all completions from CompletionID table.'''
        try:
            self.is_loading_completions = True
            self._load_k_month_data()
            
            with rx.session() as session:
                self._all_completions = session.exec(select(CompletionID)).all()
            
            self._apply_filters()
            
            # Initialize pagination
            self.completion_total_count = len(self.completions)
            self.completion_offset = 0
            
            if self.available_ids and not self.selected_id:
                self.selected_id = self.available_ids[0]
                
        except Exception as e:
            print(f"Error loading completions: {e}")
            self.completions = []
        finally:
            self.is_loading_completions = False

    def _apply_filters(self):
        '''Apply search and reservoir filters to cached completions.'''
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
        
        # Update pagination
        self.completion_total_count = len(self.completions)
        # Reset to first page when filters change
        self.completion_offset = 0
    def set_completion_page_size(self, size: str):
        '''Set page size and reset to first page.'''
        try:
            self.completion_page_size = int(size)
            self.completion_offset = 0  # Reset to first page
        except ValueError:
            pass
    
    def completion_prev_page(self, action: str = "prev"):
        '''Navigate to previous page or first page.'''
        if action == "first":
            self.completion_offset = 0
        elif self.completion_offset >= self.completion_page_size:
            self.completion_offset -= self.completion_page_size
        else:
            self.completion_offset = 0
    
    def completion_next_page(self, action: str = "next"):
        '''Navigate to next page or last page.'''
        import math
        max_offset = (self.completion_total_pages - 1) * self.completion_page_size
        
        if action == "last":
            self.completion_offset = max(0, max_offset)
        elif self.completion_offset + self.completion_page_size < self.completion_total_count:
            self.completion_offset += self.completion_page_size
    
    def completion_go_to_page(self, page: int):
        '''Navigate to specific page (1-indexed).'''
        if 1 <= page <= self.completion_total_pages:
            self.completion_offset = (page - 1) * self.completion_page_size

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
    
        Implements the exact logic:
        1. Get last history date to determine year
        2. Get all Interventions in this year and next year based on InterventionYear
        3. Apply appropriate forecast logic based on intervention status
        
        Logic:
        - No Intervention → Forecast using CompletionID → Save to ProductionForecast
        - Only Done → Forecast using InterventionID → Save to both tables (version >= 1)
        - Only Plan → Forecast using CompletionID → Save to both tables (base version = 0)
        - Mixed → Forecast using last Done → Save as base for first Plan
        """
        if not self.selected_completion or not self.forecast_end_date:
            return rx.toast.error("Please select a completion and set forecast end date")
        
        if self.qi_oil <= 0 and self.qi_liq <= 0:
            return rx.toast.error("No production history available")
        
        if self.dio <= 0:
            return rx.toast.error("Invalid decline rate (Di). Check CompletionID.Do value.")
        
        try:
            end_date = datetime.strptime(self.forecast_end_date, "%Y-%m-%d")
            
            # Get last history record
            sorted_history = sorted(self.history_prod, key=lambda x: x["Date"])
            last_prod = sorted_history[-1]
            
            start_date = last_prod["Date"]
            if isinstance(start_date, str):
                start_date = datetime.strptime(start_date, "%Y-%m-%d")
            
            if end_date <= start_date:
                return rx.toast.error(f"End date must be after {start_date.strftime('%Y-%m-%d')}")
            
            # Load KMonth data
            self._load_k_month_data()
            
            # Run forecast using the service
            with rx.session() as session:
                result = ProductionForecastService.run_forecast_for_unique_id(
                    session=session,
                    unique_id=self.selected_id,
                    completion=self.selected_completion,
                    history_data=self.history_prod,
                    end_date=end_date,
                    k_month_data=self.k_month_data
                )
            
            if not result["success"]:
                return rx.toast.error(f"Forecast failed: {result.get('error', 'Unknown error')}")
            
            # Reload data to update UI
            self._load_forecast_from_db()
            self._update_chart_data()
            
            # Build success message
            scenario = result.get("scenario", "unknown")
            total_qoil = result.get("total_qoil", 0) / 1000  # Convert to thousand tons
            
            message_parts = [
                f"Scenario: {scenario}",
                f"{result.get('months', 0)} months",
                f"Qoil: {total_qoil:.1f}kt"
            ]
            
            if result.get("done_count", 0) > 0:
                message_parts.append(f"Done GTM: {result['done_count']}")
            if result.get("plan_count", 0) > 0:
                message_parts.append(f"Plan GTM: {result['plan_count']}")
            
            return rx.toast.success(f"Forecast complete: {' | '.join(message_parts)}")
            
        except Exception as e:
            print(f"Forecast error: {e}")
            return rx.toast.error(f"Forecast error: {str(e)}")

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
        """Run DCA forecast for all completions using vectorized calculations.
        
        This method replaces the iterative approach with fully vectorized numpy
        operations for significantly better performance.
        
        Logic:
        1. Load all completion data and history
        2. Filter wells by intervention status
        3. Run vectorized exponential DCA for wells WITHOUT interventions
        4. Run individual forecasts for wells WITH interventions
        5. Save all results to ProductionForecast table
        
        DCA Formula: q(t) = qi * exp(-Di_eff * 12/365 * t)
        Effective Decline: Di_eff = Do * (1 + Dip) * (1 + Dir)
        """
        if not self.forecast_end_date:
            yield rx.toast.error("Please set forecast end date first")
            return
            
        if not self._all_completions:
            yield rx.toast.error("No completions loaded")
            return
        
        # Initialize batch state
        self.is_batch_forecasting = True
        self.batch_forecast_cancelled = False
        self.batch_forecast_progress = 0
        self.batch_forecast_total = len(self._all_completions)
        self.batch_forecast_results = []
        self.batch_forecast_errors = []
        self.batch_forecast_current = "Initializing vectorized forecast..."
        
        yield rx.toast.info(f"Starting vectorized batch forecast for {self.batch_forecast_total} completions...")
        
        try:
            end_date = datetime.strptime(self.forecast_end_date, "%Y-%m-%d")
            five_years_ago = datetime.now() - timedelta(days=5*365)
            current_year = datetime.now().year
            
            # Load KMonth data
            self._load_k_month_data()
            
            # ================================================================
            # STEP 1: PRE-LOAD ALL DATA
            # ================================================================
            self.batch_forecast_current = "Loading data..."
            yield
            
            with rx.session() as session:
                # Load all history data
                history_by_completion = DatabaseService.bulk_load_history(
                    session, HistoryProd, cutoff_date=five_years_ago
                )
                
                # Load all interventions for current year
                all_interventions = session.exec(
                    select(InterventionID).where(
                        InterventionID.InterventionYear == current_year
                    )
                ).all()
                
                # Group interventions by UniqueId
                interventions_by_uid: Dict[str, List[InterventionID]] = {}
                for intv in all_interventions:
                    if intv.UniqueId not in interventions_by_uid:
                        interventions_by_uid[intv.UniqueId] = []
                    interventions_by_uid[intv.UniqueId].append(intv)
            
            # ================================================================
            # STEP 2: SEPARATE WELLS BY INTERVENTION STATUS
            # ================================================================
            self.batch_forecast_current = "Analyzing intervention status..."
            yield
            
            wells_no_intervention = []
            wells_with_intervention = []
            
            for completion in self._all_completions:
                uid = completion.UniqueId
                
                # Check if well has history
                if uid not in history_by_completion or len(history_by_completion[uid]) == 0:
                    self.batch_forecast_errors.append(f"{uid}: No production history")
                    continue
                
                # Get last history record for qi values
                history = sorted(history_by_completion[uid], key=lambda x: x["Date"])
                last_record = history[-1]
                qi_oil = last_record["OilRate"]
                qi_liq = last_record["LiqRate"]
                
                if qi_oil <= 0 and qi_liq <= 0:
                    self.batch_forecast_errors.append(f"{uid}: Zero initial rates")
                    continue
                
                # Check for interventions
                if uid in interventions_by_uid:
                    wells_with_intervention.append({
                        "completion": completion,
                        "interventions": interventions_by_uid[uid],
                        "qi_oil": qi_oil,
                        "qi_liq": qi_liq,
                        "last_date": last_record["Date"]
                    })
                else:
                    wells_no_intervention.append({
                        "completion": completion,
                        "qi_oil": qi_oil,
                        "qi_liq": qi_liq,
                        "last_date": last_record["Date"]
                    })
            
            # ================================================================
            # STEP 3: VECTORIZED FORECAST FOR WELLS WITHOUT INTERVENTIONS
            # ================================================================
            success_count = 0
            error_count = len(self.batch_forecast_errors)
            total_qoil = 0.0
            total_qliq = 0.0
            
            if wells_no_intervention:
                self.batch_forecast_current = f"Running vectorized forecast for {len(wells_no_intervention)} wells..."
                yield
                
                try:
                    result_df, vec_errors = self._run_vectorized_exponential_forecast(
                        wells_no_intervention,
                        end_date
                    )
                    
                    if len(vec_errors) > 0:
                        self.batch_forecast_errors.extend(vec_errors)
                    
                    if len(result_df) > 0:
                        # Save vectorized results
                        with rx.session() as session:
                            for uid in result_df["UniqueId"].unique():
                                if self.batch_forecast_cancelled:
                                    break
                                
                                uid_df = result_df[result_df["UniqueId"] == uid]
                                
                                # Get next version (FIFO)
                                version = DCAService.get_next_version_fifo(
                                    session, ProductionForecast, uid,
                                    MAX_PRODUCTION_FORECAST_VERSIONS, min_version=1
                                )
                                
                                # Convert to ForecastPoints and save
                                forecast_points = []
                                for _, row in uid_df.iterrows():
                                    forecast_points.append(ForecastPoint(
                                        date=row["Date"],
                                        days_in_month=30,  # Approximate
                                        oil_rate=row["OilRate"],
                                        liq_rate=row["LiqRate"],
                                        q_oil=row["Qoil"],
                                        q_liq=row["Qliq"],
                                        wc=row["WC"]
                                    ))
                                
                                DCAService.save_forecast(
                                    session, ProductionForecast, uid,
                                    forecast_points, version
                                )
                                
                                qoil = uid_df["Qoil"].sum()
                                qliq = uid_df["Qliq"].sum()
                                total_qoil += qoil
                                total_qliq += qliq
                                success_count += 1
                                
                                self.batch_forecast_results.append({
                                    "UniqueId": uid,
                                    "Version": version,
                                    "Months": len(uid_df),
                                    "Qoil": round(qoil, 0),
                                    "Qliq": round(qliq, 0),
                                    "Type": "No Intervention",
                                    "Method": "Vectorized"
                                })
                        
                        self.batch_forecast_progress = success_count
                        yield
                        
                except Exception as e:
                    self.batch_forecast_errors.append(f"Vectorized forecast error: {str(e)}")
                    error_count += 1
            
            # ================================================================
            # STEP 4: INDIVIDUAL FORECAST FOR WELLS WITH INTERVENTIONS
            # ================================================================
            if wells_with_intervention and not self.batch_forecast_cancelled:
                self.batch_forecast_current = f"Processing {len(wells_with_intervention)} wells with interventions..."
                yield
                
                for i, well_data in enumerate(wells_with_intervention):
                    if self.batch_forecast_cancelled:
                        break
                    
                    completion = well_data["completion"]
                    uid = completion.UniqueId
                    interventions = well_data["interventions"]
                    qi_oil = well_data["qi_oil"]
                    qi_liq = well_data["qi_liq"]
                    last_date = well_data["last_date"]
                    
                    self.batch_forecast_current = f"Processing: {uid} ({i+1}/{len(wells_with_intervention)})"
                    self.batch_forecast_progress = success_count + i + 1
                    yield
                    
                    try:
                        # Use intervention-aware forecast logic
                        forecast_points = self._run_intervention_aware_forecast(
                            completion, interventions, qi_oil, qi_liq,
                            last_date, end_date
                        )
                        
                        if not forecast_points:
                            self.batch_forecast_errors.append(f"{uid}: No forecast generated")
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
                                session, ProductionForecast, uid,
                                MAX_PRODUCTION_FORECAST_VERSIONS, min_version=1
                            )
                            DCAService.save_forecast(
                                session, ProductionForecast, uid,
                                forecast_points, version
                            )
                        
                        # Determine forecast type
                        has_plan = any(i.Status == "Plan" for i in interventions)
                        has_done = any(i.Status == "Done" for i in interventions)
                        if has_plan and has_done:
                            ftype = "Done+Plan"
                        elif has_plan:
                            ftype = "Plan"
                        else:
                            ftype = "Done"
                        
                        success_count += 1
                        self.batch_forecast_results.append({
                            "UniqueId": uid,
                            "Version": version,
                            "Months": len(forecast_points),
                            "Qoil": round(qoil, 0),
                            "Qliq": round(qliq, 0),
                            "Type": ftype,
                            "Method": "Intervention"
                        })
                        
                    except Exception as e:
                        self.batch_forecast_errors.append(f"{uid}: {str(e)}")
                        error_count += 1
            
            # ================================================================
            # STEP 5: FINALIZE
            # ================================================================
            self.is_batch_forecasting = False
            self.batch_forecast_current = "Complete"
            
            if self.batch_forecast_cancelled:
                yield rx.toast.warning(
                    f"Batch cancelled. Processed {success_count}/{len(self._all_completions)}"
                )
            else:
                yield rx.toast.success(
                    f"Batch complete: {success_count} success, {error_count} errors. "
                    f"Total Qoil={total_qoil:.0f}t, Qliq={total_qliq:.0f}t"
                )
                
        except Exception as e:
            self.is_batch_forecasting = False
            self.batch_forecast_current = "Failed"
            import traceback
            traceback.print_exc()
            yield rx.toast.error(f"Batch forecast failed: {str(e)}")


    def _run_vectorized_exponential_forecast(
        self,
        wells_data: List[Dict],
        end_date: datetime
    ) -> tuple:
        """Run fully vectorized exponential DCA for multiple wells.
        
        Uses numpy broadcasting to calculate forecasts for all wells simultaneously.
        
        Args:
            wells_data: List of dicts with completion, qi_oil, qi_liq, last_date
            end_date: Forecast end date
            
        Returns:
            Tuple of (forecast_dataframe, error_list)
        """
        errors = []
        
        if len(wells_data) == 0:
            return pd.DataFrame(), errors
        
        # Find common start date (latest last_date among all wells)
        start_dates = [w["last_date"] for w in wells_data]
        # Use earliest start date to maximize forecast period
        # But align to month start for consistency
        min_start = min(start_dates)
        if isinstance(min_start, str):
            min_start = datetime.strptime(str(min_start), "%Y-%m-%d")
        
        # Generate forecast date range (month start)
        date_range = pd.date_range(min_start, end_date, freq="MS")
        if len(date_range) < 2:
            errors.append("Insufficient forecast period")
            return pd.DataFrame(), errors
        
        # Calculate elapsed days from start
        elapsed_days = np.array([(d - date_range[0]).days for d in date_range])[:-1]
        n_months = len(elapsed_days)
        n_wells = len(wells_data)
        
        # Build parameter arrays
        unique_ids = []
        dio_arr = []
        dil_arr = []
        dip_arr = []
        dir_arr = []
        qio_arr = []
        qil_arr = []
        
        for w in wells_data:
            comp = w["completion"]
            unique_ids.append(comp.UniqueId)
            dio_arr.append(comp.Do if comp.Do else 0.0)
            dil_arr.append(comp.Dl if comp.Dl else 0.0)
            dip_arr.append(comp.Dip if comp.Dip else 0.0)
            dir_arr.append(comp.Dir if comp.Dir else 0.0)
            qio_arr.append(w["qi_oil"])
            qil_arr.append(w["qi_liq"])
        
        # Convert to numpy arrays
        dio = np.array(dio_arr)
        dil = np.array(dil_arr)
        dip = np.array(dip_arr)
        dir_ = np.array(dir_arr)
        qio = np.array(qio_arr).reshape(-1, 1)
        qil = np.array(qil_arr).reshape(-1, 1)
        
        # Calculate effective decline rates
        di_oil_eff = dio * (1 + dip) * (1 + dir_)
        di_liq_eff = np.where(dil > 0, dil * (1 + dip) * (1 + dir_), di_oil_eff)
        
        # Generate working days for each month
        wk_days_oil = []
        wk_days_liq = []
        for i in range(len(date_range) - 1):
            month = date_range[i].month
            k_oil = self.k_month_data.get(month, {}).get("K_oil", 1.0)
            k_liq = self.k_month_data.get(month, {}).get("K_liq", 1.0)
            
            if month == 12:
                wk_days_oil.append(k_oil * 31.29)
                wk_days_liq.append(k_liq * 31.29)
            elif month == 1:
                wk_days_oil.append(k_oil * 30.71)
                wk_days_liq.append(k_liq * 30.71)
            else:
                days = (date_range[i + 1] - date_range[i]).days
                wk_days_oil.append(k_oil * days)
                wk_days_liq.append(k_liq * days)
        
        wk_days_oil = np.array(wk_days_oil)
        wk_days_liq = np.array(wk_days_liq)
        
        # ====================================================================
        # VECTORIZED DCA CALCULATION
        # ====================================================================
        # Rate: q(t) = qi * exp(-Di_eff * 12/365 * t)
        # Shape: (n_wells, 1) * exp((n_wells, 1) * (1, n_months)) -> (n_wells, n_months)
        
        qo_rate = qio * np.exp(-di_oil_eff.reshape(-1, 1) * elapsed_days.reshape(1, -1) * 12 / 365)
        ql_rate = qil * np.exp(-di_liq_eff.reshape(-1, 1) * elapsed_days.reshape(1, -1) * 12 / 365)
        
        # Ensure non-negative
        qo_rate = np.maximum(0.0, qo_rate)
        ql_rate = np.maximum(0.0, ql_rate)
        
        # Cumulative production: Q = rate * K * days_in_month
        Qo_cum = qo_rate * wk_days_oil  # Broadcasting: (n_wells, n_months)
        Ql_cum = ql_rate * wk_days_liq
        
        # Water cut: WC = (Qliq - Qoil) / Qliq * 100
        wc = np.where(Ql_cum > 1e-6, (Ql_cum - Qo_cum) / Ql_cum * 100, 0)
        wc = np.clip(wc, 0, 100)
        
        # Build output DataFrame
        forecast_df = pd.DataFrame({
            "UniqueId": np.repeat(unique_ids, n_months),
            "Date": np.tile(date_range[:-1], n_wells),
            "OilRate": qo_rate.flatten(),
            "LiqRate": ql_rate.flatten(),
            "Qoil": Qo_cum.flatten(),
            "Qliq": Ql_cum.flatten(),
            "WC": wc.flatten()
        })
        
        return forecast_df, errors


    def _run_intervention_aware_forecast(
        self,
        completion: CompletionID,
        interventions: List[InterventionID],
        qi_oil: float,
        qi_liq: float,
        start_date: datetime,
        end_date: datetime
    ) -> List[ForecastPoint]:
        """Run forecast for a well with interventions.
        
        Uses the existing intervention-aware logic from the state.
        
        Args:
            completion: CompletionID model
            interventions: List of InterventionID models for this well
            qi_oil: Initial oil rate
            qi_liq: Initial liquid rate  
            start_date: Last history date
            end_date: Forecast end date
            
        Returns:
            List of ForecastPoint objects
        """
        from ..utils.dca_utils import (
            arps_exponential,
            arps_decline,
            generate_forecast_dates,
            calculate_water_cut,
        )
        
        # Calculate effective decline
        dio = completion.Do if completion.Do else 0.0
        dil = completion.Dl if completion.Dl else 0.0
        dip = completion.Dip if completion.Dip else 0.0
        dir_ = completion.Dir if completion.Dir else 0.0
        
        di_oil_eff = dio * (1 + dip) * (1 + dir_)
        di_liq_eff = dil * (1 + dip) * (1 + dir_) if dil > 0 else di_oil_eff
        
        # Separate interventions by status
        done_interventions = [i for i in interventions if i.Status == "Done"]
        plan_interventions = [i for i in interventions if i.Status == "Plan"]
        
        # Sort by date
        if plan_interventions:
            plan_interventions.sort(key=lambda x: x.PlanningDate)
        if done_interventions:
            done_interventions.sort(key=lambda x: x.PlanningDate)
        
        # Generate dates
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
        
        # Default: exponential decline
        oil_rates = arps_exponential(qi_oil, di_oil_eff, elapsed_days)
        liq_rates = arps_exponential(qi_liq, di_liq_eff, elapsed_days)
        
        # If Done interventions exist, use last Done's parameters
        if done_interventions and not plan_interventions:
            last_done = done_interventions[-1]
            if last_done.InitialORate and last_done.Dio:
                qi_int = last_done.InitialORate
                di_int = last_done.Dio
                b_int = last_done.bo if last_done.bo else 0.0
                oil_rates = arps_decline(qi_int, di_int, b_int, elapsed_days)
            if last_done.InitialLRate and last_done.Dil:
                qi_liq_int = last_done.InitialLRate
                di_liq_int = last_done.Dil
                b_liq_int = last_done.bl if last_done.bl else 0.0
                liq_rates = arps_decline(qi_liq_int, di_liq_int, b_liq_int, elapsed_days)
        
        # If Plan interventions exist, merge forecasts
        if plan_interventions:
            first_plan = plan_interventions[0]
            plan_date = datetime.strptime(str(first_plan.PlanningDate)[:10], "%Y-%m-%d")
            
            # Find index where plan starts
            for idx, date in enumerate(date_range):
                dt = date.to_pydatetime() if hasattr(date, 'to_pydatetime') else date
                if dt >= plan_date:
                    # From this point, use intervention parameters
                    if first_plan.InitialORate and first_plan.Dio:
                        plan_elapsed = elapsed_days[idx:] - elapsed_days[idx]
                        b_oil = first_plan.bo if first_plan.bo else 0.0
                        oil_rates[idx:] = arps_decline(
                            first_plan.InitialORate, first_plan.Dio, b_oil, plan_elapsed
                        )
                    if first_plan.InitialLRate and first_plan.Dil:
                        plan_elapsed = elapsed_days[idx:] - elapsed_days[idx]
                        b_liq = first_plan.bl if first_plan.bl else 0.0
                        liq_rates[idx:] = arps_decline(
                            first_plan.InitialLRate, first_plan.Dil, b_liq, plan_elapsed
                        )
                    break
        
        # Ensure non-negative
        oil_rates = np.maximum(0.0, oil_rates)
        liq_rates = np.maximum(0.0, liq_rates)
        
        # Calculate cumulative
        q_oil_array = oil_rates * k_oil_array * days_in_month
        q_liq_array = liq_rates * k_liq_array * days_in_month
        
        # Build forecast points
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
    
    @rx.var
    def completion_total_pages(self) -> int:
        '''Calculate total pages for completion table.'''
        if self.completion_total_count == 0 or self.completion_page_size == 0:
            return 1
        import math
        return math.ceil(self.completion_total_count / self.completion_page_size)
    
    @rx.var
    def completion_current_page(self) -> int:
        '''Calculate current page (1-indexed).'''
        if self.completion_page_size == 0:
            return 1
        return (self.completion_offset // self.completion_page_size) + 1
    
    @rx.var
    def completion_start_item(self) -> int:
        '''First item index on current page (1-indexed for display).'''
        if self.completion_total_count == 0:
            return 0
        return self.completion_offset + 1
    
    @rx.var
    def completion_end_item(self) -> int:
        '''Last item index on current page (1-indexed for display).'''
        end = self.completion_offset + self.completion_page_size
        return min(end, self.completion_total_count)
    
    @rx.var
    def paginated_completions(self) -> List[CompletionID]:
        '''Get completions for current page after filtering.'''
        start = self.completion_offset
        end = start + self.completion_page_size
        return self.completions[start:end]