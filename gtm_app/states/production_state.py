"""Refactored Production State with Dip/Dir support.

This state manages Production monitoring and forecasting with:
- Dip: Platform-level decline adjustment
- Dir: Reservoir+Field level decline adjustment
- Effective Di = Do * (1 + Dip) * (1 + Dir)

DCA Formula: q(t) = qi * exp(-Di_eff * 12/365 * t)
Cumulative: Qoil = OilRate * K_oil * days_in_month
"""
import reflex as rx
from typing import Optional, List, Tuple
from datetime import datetime, timedelta
from sqlmodel import select, delete, func, desc, or_

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


class ProductionState(SharedForecastState):
    """State for Production monitoring and forecasting with Dip/Dir support."""
    
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
    dip: float = 0.0  # Platform-level adjustment
    dir: float = 0.0  # Reservoir+Field level adjustment
    
    # Intervention status
    has_planned_intervention: bool = False
    intervention_info: str = ""
    
    # Search/filter
    search_value: str = ""
    selected_reservoir: str = ""
    
    # Loading states
    is_loading_completions: bool = False
    is_loading_production: bool = False
    
    # ========== Batch Forecast State ==========
    is_batch_forecasting: bool = False
    batch_forecast_progress: int = 0
    batch_forecast_total: int = 0
    batch_forecast_current: str = ""
    batch_forecast_results: List[dict] = []
    batch_forecast_errors: List[str] = []
    batch_forecast_cancelled: bool = False

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
                #self.load_production_data_background()
                
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
                
                # Update all decline parameters
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
            has_intervention = False
            intervention_text = ""
            
            with rx.session() as session:
                history_data = DCAService.load_history_data(session, unique_id, years=5)
                
                intervention = session.exec(
                    select(InterventionID).where(
                        InterventionID.UniqueId == unique_id,
                        InterventionID.Status == "Plan"
                    )
                ).first()
                
                has_intervention = intervention is not None
                if intervention:
                    intervention_text = f"{intervention.TypeGTM} planned on {intervention.PlanningDate}"
                
                forecast_versions = DatabaseService.get_available_versions(
                    session, ProductionForecast, unique_id, min_version=1
                )
            
            async with self:
                self.history_prod = history_data
                self.has_planned_intervention = has_intervention
                self.intervention_info = intervention_text
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

    def run_forecast(self):
        """Run DCA forecast using service with Dip/Dir adjustments."""
        if not self.selected_completion or not self.forecast_end_date:
            return rx.toast.error("Please select a completion and set forecast end date")
        
        if self.qi_oil <= 0 and self.qi_liq <= 0:
            return rx.toast.error("No production history available")
        
        if self.dio <= 0:
            return rx.toast.error("Invalid decline rate (Di). Check CompletionID.Do value.")
        
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
            
            self._load_k_month_data()
            
            # Create forecast config with Dip/Dir
            config = ForecastConfig(
                qi_oil=self.qi_oil,
                di_oil=self.dio,
                b_oil=self.b_oil,
                qi_liq=self.qi_liq,
                di_liq=self.dil,
                b_liq=self.b_liq,
                start_date=start_date,
                end_date=end_date,
                use_exponential=self.use_exponential_dca,
                k_month_data=self.k_month_data,
                dip=self.dip,
                dir=self.dir
            )
            
            # Run forecast using service
            result = DCAService.run_production_forecast(config)
            
            if not result.is_success:
                return rx.toast.error(result.error or "Forecast failed")
            
            # Save to database
            with rx.session() as session:
                version = DCAService.get_next_version_fifo(
                    session, ProductionForecast, self.selected_id,
                    MAX_PRODUCTION_FORECAST_VERSIONS, min_version=1
                )
                DCAService.save_forecast(
                    session, ProductionForecast, self.selected_id,
                    result.forecast_points, version
                )
                
                # Save to InterventionForecast if intervention planned
                if self.has_planned_intervention:
                    DCAService.save_forecast(
                        session, InterventionForecast, self.selected_id,
                        result.forecast_points, version=0, data_type="Forecast"
                    )
            
            # Update state
            self.forecast_data = DCAService.forecast_to_dict_list(result.forecast_points)
            self.current_forecast_version = version
            
            with rx.session() as session:
                self.available_forecast_versions = DatabaseService.get_available_versions(
                    session, ProductionForecast, self.selected_id, min_version=1
                )
            
            self._update_chart_data()
            
            msg = (
                f"Forecast v{version}: {result.months} months, "
                f"Di_eff={result.effective_di_oil:.4f}, Qoil={result.total_qoil:.0f}t"
            )
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

    def cancel_batch_forecast(self):
        """Cancel the running batch forecast."""
        self.batch_forecast_cancelled = True
        return rx.toast.warning("Batch forecast cancellation requested...")

    def run_forecast_all(self):
        """Run DCA forecast for all completions with Dip/Dir."""
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
            
            self._load_k_month_data()
            
            with rx.session() as session:
                history_by_completion = DatabaseService.bulk_load_history(
                    session, HistoryProd, cutoff_date=five_years_ago
                )
                
                planned_interventions = session.exec(
                    select(InterventionID.UniqueId).where(InterventionID.Status == "Plan")
                ).all()
                intervention_ids = set(planned_interventions)
            
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
                
                sorted_history = sorted(history, key=lambda x: x["Date"])
                last_prod = sorted_history[-1]
                
                di_oil = completion.Do if completion.Do and completion.Do > 0 else 0.0
                
                if di_oil <= 0:
                    self.batch_forecast_errors.append(f"{unique_id}: Invalid Di")
                    error_count += 1
                    continue
                
                start_date = last_prod["Date"]
                if isinstance(start_date, str):
                    start_date = datetime.strptime(start_date, "%Y-%m-%d")
                
                # Get Dip and Dir from completion
                dip = completion.Dip if completion.Dip else 0.0
                dir_val = completion.Dir if completion.Dir else 0.0
                
                config = ForecastConfig(
                    qi_oil=last_prod["OilRate"],
                    di_oil=di_oil,
                    b_oil=0.0,
                    qi_liq=last_prod["LiqRate"],
                    di_liq=completion.Dl if completion.Dl and completion.Dl > 0 else di_oil,
                    b_liq=0.0,
                    start_date=start_date,
                    end_date=end_date,
                    use_exponential=True,
                    k_month_data=self.k_month_data,
                    dip=dip,
                    dir=dir_val
                )
                
                result = DCAService.run_production_forecast(config)
                
                if not result.is_success:
                    self.batch_forecast_errors.append(f"{unique_id}: {result.error}")
                    error_count += 1
                    continue
                
                total_qoil += result.total_qoil
                total_qliq += result.total_qliq
                
                try:
                    with rx.session() as session:
                        version = DCAService.get_next_version_fifo(
                            session, ProductionForecast, unique_id,
                            MAX_PRODUCTION_FORECAST_VERSIONS, min_version=1
                        )
                        DCAService.save_forecast(
                            session, ProductionForecast, unique_id,
                            result.forecast_points, version
                        )
                        
                        if unique_id in intervention_ids:
                            DCAService.save_forecast(
                                session, InterventionForecast, unique_id,
                                result.forecast_points, version=0, data_type="Forecast"
                            )
                    
                    success_count += 1
                    self.batch_forecast_results.append({
                        "UniqueId": unique_id,
                        "Version": version,
                        "Months": result.months,
                        "Qoil": round(result.total_qoil, 0),
                        "Qliq": round(result.total_qliq, 0),
                        "Di_eff": round(result.effective_di_oil, 4)
                    })
                    
                except Exception as e:
                    self.batch_forecast_errors.append(f"{unique_id}: Save error - {str(e)}")
                    error_count += 1
            
            self.is_batch_forecasting = False
            self.batch_forecast_current = "Complete"
            
            if self.batch_forecast_cancelled:
                yield rx.toast.warning(
                    f"Batch forecast cancelled. Processed {success_count} of {len(self.completions)} completions."
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
        """Get unique platforms from WellID for batch Dip updates."""
        from ..models import PLATFORM_OPTIONS
        return PLATFORM_OPTIONS
    
    @rx.var
    def unique_fields(self) -> List[str]:
        """Get unique fields for batch Dir updates."""
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
        """Calculate effective oil decline rate."""
        return self.dio * (1 + self.dip) * (1 + self.dir)
    
    @rx.var
    def effective_di_display(self) -> str:
        """Display effective decline rate."""
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