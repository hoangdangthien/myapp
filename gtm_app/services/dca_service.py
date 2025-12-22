"""DCA Service - Centralized decline curve analysis operations.

This service provides:
- Arps decline curve calculations (Exponential, Hyperbolic, Harmonic)
- Forecast generation with KMonth integration
- Version management with FIFO logic
- Cumulative production calculations
- Dip (Platform) and Dir (Reservoir+Field) adjustment support

Key Formula:
- Effective Decline: Di_eff = Do * (1 + Dip) * (1 + Dir)
- Exponential: q(t) = qi * exp(-Di_eff * 12/365 * t) where t is elapsed days
- Cumulative: Qoil = OilRate * K * days_in_month
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from sqlmodel import select, delete, func

from ..utils.dca_utils import (
    arps_exponential,
    arps_decline,
    generate_forecast_dates,
    calculate_water_cut,
    run_dca_forecast,
    run_dca_forecast_intervention,
    ForecastPoint,
)


@dataclass
class ForecastConfig:
    """Configuration for DCA forecast.
    
    Attributes:
        qi_oil: Initial oil rate (t/day)
        di_oil: Base oil decline rate (1/year)
        b_oil: Arps b parameter for oil
        qi_liq: Initial liquid rate (t/day)
        di_liq: Base liquid decline rate (1/year)
        b_liq: Arps b parameter for liquid
        start_date: Forecast start date
        end_date: Forecast end date
        use_exponential: Use exponential decline (True) or hyperbolic (False)
        k_month_data: Monthly K factors
        dip: Platform-level decline adjustment factor
        dir: Reservoir+Field level decline adjustment factor
    """
    qi_oil: float
    di_oil: float
    b_oil: float
    qi_liq: float
    di_liq: float
    b_liq: float
    start_date: datetime
    end_date: datetime
    use_exponential: bool = True
    k_month_data: Dict[int, Dict[str, float]] = None
    dip: float = 0.0  # Platform-level adjustment
    dir: float = 0.0  # Reservoir+Field level adjustment
    
    def __post_init__(self):
        if self.k_month_data is None:
            self.k_month_data = {
                i: {"K_oil": 1.0, "K_liq": 1.0, "K_int": 1.0, "K_inj": 1.0}
                for i in range(1, 13)
            }
    
    @property
    def effective_di_oil(self) -> float:
        """Calculate effective oil decline rate with adjustments.
        
        Formula: Di_eff = Do * (1 + Dip) * (1 + Dir)
        """
        return self.di_oil * (1 + self.dip) * (1 + self.dir)
    
    @property
    def effective_di_liq(self) -> float:
        """Calculate effective liquid decline rate with adjustments.
        
        Formula: Di_eff = Dl * (1 + Dip) * (1 + Dir)
        """
        return self.di_liq * (1 + self.dip) * (1 + self.dir)


@dataclass
class ForecastResult:
    """Result of a DCA forecast operation."""
    forecast_points: List[ForecastPoint]
    total_qoil: float
    total_qliq: float
    months: int
    version: int = 0
    error: str = ""
    effective_di_oil: float = 0.0
    effective_di_liq: float = 0.0
    
    @property
    def is_success(self) -> bool:
        return len(self.forecast_points) > 0 and not self.error


class DCAService:
    """Service class for DCA operations."""
    
    DEFAULT_K_MONTH = {
        i: {"K_oil": 1.0, "K_liq": 1.0, "K_int": 1.0, "K_inj": 1.0}
        for i in range(1, 13)
    }
    
    @staticmethod
    def calculate_effective_decline(
        base_di: float,
        dip: float = 0.0,
        dir: float = 0.0
    ) -> float:
        """Calculate effective decline rate with adjustments.
        
        Formula: Di_eff = Do * (1 + Dip) * (1 + Dir)
        
        Args:
            base_di: Base decline rate (1/year)
            dip: Platform-level adjustment factor
            dir: Reservoir+Field level adjustment factor
            
        Returns:
            Effective decline rate
        """
        return base_di * (1 + dip) * (1 + dir)
    
    @staticmethod
    def load_k_month_data(session) -> Dict[int, Dict[str, float]]:
        """Load KMonth data from database."""
        from ..models import KMonth
        
        try:
            k_records = session.exec(select(KMonth)).all()
            if not k_records:
                return DCAService.DEFAULT_K_MONTH.copy()
            
            return {
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
            return DCAService.DEFAULT_K_MONTH.copy()
    
    @staticmethod
    def load_decline_adjustments(
        session,
        platform: str = None,
        field: str = None,
        reservoir: str = None
    ) -> Tuple[float, float]:
        """Load Dip and Dir from DeclineAdjustment table.
        
        Args:
            session: Database session
            platform: Platform name for Dip lookup
            field: Field name for Dir lookup
            reservoir: Reservoir name for Dir lookup
            
        Returns:
            Tuple of (dip, dir)
        """
        from ..models import DeclineAdjustment
        
        dip = 0.0
        dir_val = 0.0
        
        try:
            # Load Dip (platform-level)
            if platform:
                dip_record = session.exec(
                    select(DeclineAdjustment).where(
                        DeclineAdjustment.AdjustmentType == "Platform",
                        DeclineAdjustment.Platform == platform
                    )
                ).first()
                if dip_record:
                    dip = dip_record.AdjustmentValue
            
            # Load Dir (reservoir+field level)
            if field and reservoir:
                dir_record = session.exec(
                    select(DeclineAdjustment).where(
                        DeclineAdjustment.AdjustmentType == "ReservoirField",
                        DeclineAdjustment.Field == field,
                        DeclineAdjustment.Reservoir == reservoir
                    )
                ).first()
                if dir_record:
                    dir_val = dir_record.AdjustmentValue
        
        except Exception as e:
            print(f"Error loading decline adjustments: {e}")
        
        return dip, dir_val
    
    @staticmethod
    def run_production_forecast(config: ForecastConfig) -> ForecastResult:
        """Run DCA forecast for production monitoring.
        
        Uses effective decline rates incorporating Dip and Dir adjustments.
        
        Args:
            config: Forecast configuration
            
        Returns:
            ForecastResult with forecast data
        """
        try:
            # Validate inputs
            if config.qi_oil <= 0 and config.qi_liq <= 0:
                return ForecastResult([], 0, 0, 0, error="No production data")
            
            if config.di_oil <= 0:
                return ForecastResult([], 0, 0, 0, error="Invalid Di (oil)")
            
            if config.end_date <= config.start_date:
                return ForecastResult([], 0, 0, 0, error="Invalid date range")
            
            # Calculate effective decline rates
            di_oil_eff = config.effective_di_oil
            di_liq_eff = config.effective_di_liq if config.di_liq > 0 else di_oil_eff
            
            # Run DCA forecast with effective rates
            forecast_points = run_dca_forecast(
                start_date=config.start_date,
                end_date=config.end_date,
                qi_oil=config.qi_oil,
                di_oil=di_oil_eff,
                b_oil=config.b_oil,
                qi_liq=config.qi_liq,
                di_liq=di_liq_eff,
                b_liq=config.b_liq,
                k_month_data=config.k_month_data,
                use_exponential=config.use_exponential
            )
            
            if not forecast_points:
                return ForecastResult([], 0, 0, 0, error="No forecast generated")
            
            total_qoil = sum(fp.q_oil for fp in forecast_points)
            total_qliq = sum(fp.q_liq for fp in forecast_points)
            
            return ForecastResult(
                forecast_points=forecast_points,
                total_qoil=total_qoil,
                total_qliq=total_qliq,
                months=len(forecast_points),
                effective_di_oil=di_oil_eff,
                effective_di_liq=di_liq_eff
            )
            
        except Exception as e:
            return ForecastResult([], 0, 0, 0, error=str(e))
    
    @staticmethod
    def run_intervention_forecast(config: ForecastConfig) -> ForecastResult:
        """Run DCA forecast for intervention.
        
        Uses K_int factor for cumulative calculations and effective decline rates.
        
        Args:
            config: Forecast configuration
            
        Returns:
            ForecastResult with forecast data
        """
        try:
            # Validate inputs
            if config.qi_oil <= 0 and config.qi_liq <= 0:
                return ForecastResult([], 0, 0, 0, error="No production data")
            
            if config.di_oil <= 0:
                return ForecastResult([], 0, 0, 0, error="Invalid Di (oil)")
            
            if config.end_date <= config.start_date:
                return ForecastResult([], 0, 0, 0, error="Invalid date range")
            
            # Calculate effective decline rates
            di_oil_eff = config.effective_di_oil
            di_liq_eff = config.effective_di_liq if config.di_liq > 0 else di_oil_eff
            
            # Run intervention DCA forecast
            forecast_points = run_dca_forecast_intervention(
                start_date=config.start_date,
                end_date=config.end_date,
                qi_oil=config.qi_oil,
                di_oil=di_oil_eff,
                b_oil=config.b_oil,
                qi_liq=config.qi_liq,
                di_liq=di_liq_eff,
                b_liq=config.b_liq,
                k_month_data=config.k_month_data,
                use_exponential=config.use_exponential
            )
            
            if not forecast_points:
                return ForecastResult([], 0, 0, 0, error="No forecast generated")
            
            total_qoil = sum(fp.q_oil for fp in forecast_points)
            total_qliq = sum(fp.q_liq for fp in forecast_points)
            
            return ForecastResult(
                forecast_points=forecast_points,
                total_qoil=total_qoil,
                total_qliq=total_qliq,
                months=len(forecast_points),
                effective_di_oil=di_oil_eff,
                effective_di_liq=di_liq_eff
            )
            
        except Exception as e:
            return ForecastResult([], 0, 0, 0, error=str(e))
    
    @staticmethod
    def get_next_version_fifo(
        session,
        model_class,
        unique_id: str,
        max_versions: int,
        min_version: int = 1
    ) -> int:
        """Get next forecast version using FIFO logic."""
        existing_versions = session.exec(
            select(model_class.Version, func.min(model_class.CreatedAt))
            .where(
                model_class.UniqueId == unique_id,
                model_class.Version >= min_version
            )
            .group_by(model_class.Version)
        ).all()
        
        if not existing_versions:
            return min_version if min_version > 0 else 1
        
        used_versions = [v[0] for v in existing_versions]
        
        if len(used_versions) < max_versions:
            for v in range(min_version if min_version > 0 else 1, max_versions + 1):
                if v not in used_versions:
                    return v
        
        oldest_version = min(existing_versions, key=lambda x: x[1])[0]
        
        session.exec(
            delete(model_class).where(
                model_class.UniqueId == unique_id,
                model_class.Version == oldest_version
            )
        )
        session.commit()
        
        return oldest_version
    
    @staticmethod
    def save_forecast(
        session,
        model_class,
        unique_id: str,
        forecast_points: List[ForecastPoint],
        version: int,
        data_type: str = "Forecast"
    ) -> None:
        """Save forecast points to database."""
        created_at = datetime.now()
        
        session.exec(
            delete(model_class).where(
                model_class.UniqueId == unique_id,
                model_class.Version == version
            )
        )
        session.commit()
        
        for fp in forecast_points:
            record_data = {
                "UniqueId": unique_id,
                "Date": fp.date,
                "Version": version,
                "OilRate": fp.oil_rate,
                "LiqRate": fp.liq_rate,
                "Qoil": fp.q_oil,
                "Qliq": fp.q_liq,
                "WC": fp.wc,
                "CreatedAt": created_at
            }
            
            if hasattr(model_class, "DataType"):
                record_data["DataType"] = data_type
            
            record = model_class(**record_data)
            session.add(record)
        
        session.commit()
    
    @staticmethod
    def load_history_data(
        session,
        unique_id: str,
        years: int = 5
    ) -> List[Dict[str, Any]]:
        """Load production history data."""
        from ..models import HistoryProd
        from sqlmodel import desc
        
        cutoff_date = datetime.now() - timedelta(days=years * 365)
        
        history_records = session.exec(
            select(HistoryProd).where(
                HistoryProd.UniqueId == unique_id,
                HistoryProd.Date >= cutoff_date
            ).order_by(desc(HistoryProd.Date))
        ).all()
        
        result = []
        for rec in history_records:
            oil_rate = rec.OilRate if rec.OilRate else 0.0
            liq_rate = rec.LiqRate if rec.LiqRate else 0.0
            wc = calculate_water_cut(oil_rate, liq_rate)
            
            result.append({
                "UniqueId": rec.UniqueId,
                "Date": rec.Date,
                "OilRate": oil_rate,
                "LiqRate": liq_rate,
                "WC": round(wc, 2),
                "GOR": rec.GOR if rec.GOR else 0.0,
                "Dayon": rec.Dayon if rec.Dayon else 0.0,
                "Method": rec.Method if rec.Method else ""
            })
        
        return result
    
    @staticmethod
    def forecast_to_dict_list(forecast_points: List[ForecastPoint]) -> List[Dict]:
        """Convert forecast points to list of dictionaries."""
        return [
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
    
    @staticmethod
    def build_chart_data(
        history_prod: List[Dict],
        forecast_data: List[Dict],
        base_forecast_data: List[Dict] = None
    ) -> List[Dict]:
        """Build unified chart data combining actual, forecast, and base forecast.
        
        Key improvements for continuous time series visualization:
        1. Use a dictionary keyed by date to merge overlapping points
        2. Add transition point: last actual values also appear as first forecast point
        3. Ensure continuous lines between history and forecast
        
        Args:
            history_prod: List of historical production records
            forecast_data: List of forecast data points
            base_forecast_data: Optional base case forecast for comparison
            
        Returns:
            Sorted list of chart data points with merged values
        """
        # Use dict to merge points by date - prevents duplicate dates
        chart_dict: Dict[str, Dict] = {}
        
        # Track last actual point for creating transition
        last_actual_date = None
        last_actual_oil = 0.0
        last_actual_liq = 0.0
        last_actual_wc = 0.0
        
        # Process history data first
        sorted_history = sorted(history_prod, key=lambda x: x["Date"])
        for prod in sorted_history:
            date_val = prod["Date"]
            # Normalize date string format
            if isinstance(date_val, datetime):
                date_str = date_val.strftime("%Y-%m-%d")
            else:
                # Handle string dates - ensure consistent format
                try:
                    parsed_date = datetime.strptime(str(date_val)[:10], "%Y-%m-%d")
                    date_str = parsed_date.strftime("%Y-%m-%d")
                except:
                    date_str = str(date_val)[:10]
            
            oil_rate = float(prod["OilRate"]) if prod["OilRate"] else 0.0
            liq_rate = float(prod["LiqRate"]) if prod["LiqRate"] else 0.0
            wc = float(prod["WC"]) if prod["WC"] else 0.0
            
            # Initialize or update chart point
            if date_str not in chart_dict:
                chart_dict[date_str] = {"date": date_str}
            
            chart_dict[date_str]["oilRate"] = oil_rate
            chart_dict[date_str]["liqRate"] = liq_rate
            chart_dict[date_str]["wc"] = wc
            chart_dict[date_str]["type"] = "actual"
            
            # Track last actual for transition point
            last_actual_date = date_str
            last_actual_oil = oil_rate
            last_actual_liq = liq_rate
            last_actual_wc = wc
        
        # Process forecast data
        for i, fc in enumerate(forecast_data):
            date_str = fc["date"]
            # Normalize date string
            if isinstance(date_str, datetime):
                date_str = date_str.strftime("%Y-%m-%d")
            else:
                date_str = str(date_str)[:10]
            
            oil_rate = float(fc["oilRate"]) if fc["oilRate"] else 0.0
            liq_rate = float(fc["liqRate"]) if fc["liqRate"] else 0.0
            wc_forecast = float(fc.get("wc", 0)) if fc.get("wc") else calculate_water_cut(oil_rate, liq_rate)
            
            if date_str not in chart_dict:
                chart_dict[date_str] = {"date": date_str}
            
            chart_dict[date_str]["oilRateForecast"] = oil_rate
            chart_dict[date_str]["liqRateForecast"] = liq_rate
            chart_dict[date_str]["wcForecast"] = round(wc_forecast, 2)
            
            # Mark point type
            if chart_dict[date_str].get("type") == "actual":
                chart_dict[date_str]["type"] = "transition"
            else:
                chart_dict[date_str]["type"] = "forecast"
        
        # Create transition point: Add last actual values to forecast series
        # This ensures the forecast line connects to the history line
        if last_actual_date and forecast_data:
            if last_actual_date in chart_dict:
                point = chart_dict[last_actual_date]
                # Only add if forecast values not already present at this date
                if "oilRateForecast" not in point:
                    point["oilRateForecast"] = last_actual_oil
                    point["liqRateForecast"] = last_actual_liq
                    point["wcForecast"] = last_actual_wc
                    point["type"] = "transition"
        
        # Process base forecast data (for intervention comparison)
        if base_forecast_data:
            # Add transition from last actual to base forecast
            if last_actual_date:
                if last_actual_date in chart_dict:
                    point = chart_dict[last_actual_date]
                    if "oilRateBase" not in point:
                        point["oilRateBase"] = last_actual_oil
                        point["liqRateBase"] = last_actual_liq
                        point["wcBase"] = last_actual_wc
            
            for bf in base_forecast_data:
                date_str = bf["date"]
                if isinstance(date_str, datetime):
                    date_str = date_str.strftime("%Y-%m-%d")
                else:
                    date_str = str(date_str)[:10]
                
                oil_rate = float(bf["oilRate"]) if bf["oilRate"] else 0.0
                liq_rate = float(bf["liqRate"]) if bf["liqRate"] else 0.0
                wc_base = float(bf.get("wc", 0)) if bf.get("wc") else calculate_water_cut(oil_rate, liq_rate)
                
                if date_str not in chart_dict:
                    chart_dict[date_str] = {"date": date_str, "type": "base_forecast"}
                
                chart_dict[date_str]["oilRateBase"] = oil_rate
                chart_dict[date_str]["liqRateBase"] = liq_rate
                chart_dict[date_str]["wcBase"] = round(wc_base, 2)
        
        # Convert to sorted list
        chart_points = list(chart_dict.values())
        chart_points.sort(key=lambda x: x["date"])
        
        return chart_points