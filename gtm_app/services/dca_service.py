"""DCA Service - Centralized decline curve analysis operations.

This service provides:
- Arps decline curve calculations (Exponential, Hyperbolic, Harmonic)
- Forecast generation with KMonth integration
- Version management with FIFO logic
- Cumulative production calculations

Key Formula:
- Exponential: q(t) = qi * exp(-di * 12/365 * t) where t is elapsed days
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
    """Configuration for DCA forecast."""
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
    
    def __post_init__(self):
        if self.k_month_data is None:
            self.k_month_data = {
                i: {"K_oil": 1.0, "K_liq": 1.0, "K_int": 1.0, "K_inj": 1.0}
                for i in range(1, 13)
            }


@dataclass
class ForecastResult:
    """Result of a DCA forecast operation."""
    forecast_points: List[ForecastPoint]
    total_qoil: float
    total_qliq: float
    months: int
    version: int = 0
    error: str = ""
    
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
    def load_k_month_data(session) -> Dict[int, Dict[str, float]]:
        """Load KMonth data from database.
        
        Args:
            session: Database session
            
        Returns:
            Dictionary mapping month_id to K factors
        """
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
    def run_production_forecast(config: ForecastConfig) -> ForecastResult:
        """Run DCA forecast for production monitoring.
        
        Uses K_oil and K_liq factors.
        
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
            
            # Run DCA forecast
            forecast_points = run_dca_forecast(
                start_date=config.start_date,
                end_date=config.end_date,
                qi_oil=config.qi_oil,
                di_oil=config.di_oil,
                b_oil=config.b_oil,
                qi_liq=config.qi_liq,
                di_liq=config.di_liq if config.di_liq > 0 else config.di_oil,
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
                months=len(forecast_points)
            )
            
        except Exception as e:
            return ForecastResult([], 0, 0, 0, error=str(e))
    
    @staticmethod
    def run_intervention_forecast(config: ForecastConfig) -> ForecastResult:
        """Run DCA forecast for intervention.
        
        Uses K_int factor for cumulative calculations.
        
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
            
            # Run intervention DCA forecast
            forecast_points = run_dca_forecast_intervention(
                start_date=config.start_date,
                end_date=config.end_date,
                qi_oil=config.qi_oil,
                di_oil=config.di_oil,
                b_oil=config.b_oil,
                qi_liq=config.qi_liq,
                di_liq=config.di_liq if config.di_liq > 0 else config.di_oil,
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
                months=len(forecast_points)
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
        """Get next forecast version using FIFO logic.
        
        Args:
            session: Database session
            model_class: The model class (ProductionForecast or InterventionForecast)
            unique_id: The unique identifier
            max_versions: Maximum number of versions to keep
            min_version: Minimum version number (1 for regular, 0 for base)
            
        Returns:
            Next available version number
        """
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
        
        # If we have room, find unused version
        if len(used_versions) < max_versions:
            for v in range(min_version if min_version > 0 else 1, max_versions + 1):
                if v not in used_versions:
                    return v
        
        # Otherwise, delete oldest and reuse its version
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
        """Save forecast points to database.
        
        Args:
            session: Database session
            model_class: The model class
            unique_id: The unique identifier
            forecast_points: List of forecast points
            version: Version number
            data_type: Type of data (Forecast/Actual)
        """
        created_at = datetime.now()
        
        # Delete existing records for this version
        session.exec(
            delete(model_class).where(
                model_class.UniqueId == unique_id,
                model_class.Version == version
            )
        )
        session.commit()
        
        # Insert new records
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
            
            # Add DataType for InterventionForecast
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
        """Load production history data.
        
        Args:
            session: Database session
            unique_id: The unique identifier
            years: Number of years to load
            
        Returns:
            List of history records as dictionaries
        """
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
        """Convert forecast points to list of dictionaries.
        
        Args:
            forecast_points: List of ForecastPoint objects
            
        Returns:
            List of dictionaries for state storage
        """
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
        
        Args:
            history_prod: Historical production data
            forecast_data: Forecast data (intervention or production)
            base_forecast_data: Base case forecast (optional, for intervention)
            
        Returns:
            Combined chart data sorted by date
        """
        chart_points = []
        
        # Add actual history data
        sorted_history = sorted(history_prod, key=lambda x: x["Date"])
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
        
        # Add forecast data
        for fc in forecast_data:
            wc_forecast = calculate_water_cut(fc["oilRate"], fc["liqRate"])
            chart_points.append({
                "date": fc["date"],
                "oilRateForecast": fc["oilRate"],
                "liqRateForecast": fc["liqRate"],
                "wcForecast": round(wc_forecast, 2),
                "type": "forecast"
            })
        
        # Add base forecast data if provided
        if base_forecast_data:
            for bf in base_forecast_data:
                wc_base = calculate_water_cut(bf["oilRate"], bf["liqRate"])
                
                # Check if this date already exists
                existing_point = next(
                    (p for p in chart_points if p["date"] == bf["date"]),
                    None
                )
                
                if existing_point:
                    existing_point["oilRateBase"] = bf["oilRate"]
                    existing_point["liqRateBase"] = bf["liqRate"]
                    existing_point["wcBase"] = round(wc_base, 2)
                else:
                    chart_points.append({
                        "date": bf["date"],
                        "oilRateBase": bf["oilRate"],
                        "liqRateBase": bf["liqRate"],
                        "wcBase": round(wc_base, 2),
                        "type": "base_forecast"
                    })
        
        # Sort by date
        chart_points.sort(key=lambda x: x["date"])
        
        return chart_points