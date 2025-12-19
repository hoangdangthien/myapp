"""DCA (Decline Curve Analysis) utility functions.

This module provides:
- Arps decline curve functions (exponential, hyperbolic, harmonic)
- Date range generation with pandas
- KMonth integration for cumulative production calculation
- Elapsed days calculation per month
"""
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Tuple, List, Dict, Optional
from dataclasses import dataclass


@dataclass
class ArpsParameters:
    """Arps decline curve parameters."""
    qi: float  # Initial rate
    di: float  # Initial decline rate (1/month)
    b: float = 0.0  # Decline exponent (0=exponential, 0<b<1=hyperbolic, b=1=harmonic)


@dataclass
class ForecastPoint:
    """Single forecast data point."""
    date: datetime
    days_in_month: int
    oil_rate: float
    liq_rate: float
    q_oil: float  # Cumulative oil production in month
    q_liq: float  # Cumulative liquid production in month
    wc: float  # Water cut percentage


def arps_exponential(qi: float, di: float, t: float) -> float:
    """Exponential decline: q(t) = qi * exp(-di * t)
    
    Args:
        qi: Initial rate (t/day or bbl/day)
        di: Decline rate (1/month)
        t: Time in months
    
    Returns:
        Rate at time t
    """
    if di <= 0:
        return qi
    return qi * np.exp(-di * t)


def arps_hyperbolic(qi: float, di: float, b: float, t: float) -> float:
    """Hyperbolic decline: q(t) = qi / (1 + b * di * t)^(1/b)
    
    Args:
        qi: Initial rate
        di: Initial decline rate (1/month)
        b: Decline exponent (0 < b < 1)
        t: Time in months
    
    Returns:
        Rate at time t
    """
    if di <= 0 or b <= 0:
        return qi
    return qi / ((1 + b * di * t) ** (1 / b))


def arps_harmonic(qi: float, di: float, t: float) -> float:
    """Harmonic decline: q(t) = qi / (1 + di * t)
    
    Special case of hyperbolic where b = 1
    
    Args:
        qi: Initial rate
        di: Decline rate (1/month)
        t: Time in months
    
    Returns:
        Rate at time t
    """
    if di <= 0:
        return qi
    return qi / (1 + di * t)


def arps_decline(qi: float, di: float, b: float, t: float) -> float:
    """General Arps decline function that selects appropriate model.
    
    Args:
        qi: Initial rate
        di: Initial decline rate (1/month)
        b: Decline exponent
            - b = 0: Exponential decline
            - 0 < b < 1: Hyperbolic decline
            - b = 1: Harmonic decline
        t: Time in months
    
    Returns:
        Rate at time t
    """
    if b == 0 or b < 0.001:  # Exponential
        return arps_exponential(qi, di, t)
    elif abs(b - 1.0) < 0.001:  # Harmonic
        return arps_harmonic(qi, di, t)
    else:  # Hyperbolic
        return arps_hyperbolic(qi, di, b, t)


def generate_monthly_dates(start_date: datetime, end_date: datetime) -> pd.DatetimeIndex:
    """Generate monthly date range using pandas.
    
    Args:
        start_date: Start date of forecast
        end_date: End date of forecast
    
    Returns:
        DatetimeIndex with monthly dates (start of month)
    """
    return pd.date_range(start=start_date, end=end_date, freq="MS")


def calculate_elapsed_days(date_range: pd.DatetimeIndex) -> List[int]:
    """Calculate number of days in each month from date range.
    
    Args:
        date_range: DatetimeIndex of monthly dates
    
    Returns:
        List of days in each month
    """
    days_list = []
    for date in date_range:
        # Get number of days in the month
        days_in_month = pd.Period(date, freq='M').days_in_month
        days_list.append(days_in_month)
    return days_list


def get_month_index(date: datetime) -> int:
    """Get month index (1-12) from date for KMonth lookup.
    
    Args:
        date: Date to get month from
    
    Returns:
        Month index (1=January, 12=December)
    """
    return date.month


def calculate_cumulative_production(
    rate: float,
    days_in_month: int,
    k_factor: float
) -> float:
    """Calculate cumulative production for a month.
    
    Formula: Q = K * days_in_month * rate
    
    Args:
        rate: Production rate (t/day)
        days_in_month: Number of days in the month
        k_factor: Uptime factor from KMonth table (0-1)
    
    Returns:
        Cumulative production for the month (tons)
    """
    return k_factor * days_in_month * rate


def calculate_water_cut(oil_rate: float, liq_rate: float) -> float:
    """Calculate water cut percentage.
    
    Formula: WC = (Liqrate - Oilrate) / Liqrate * 100
    
    Args:
        oil_rate: Oil production rate
        liq_rate: Liquid production rate
    
    Returns:
        Water cut percentage (0-100)
    """
    if liq_rate <= 0:
        return 0.0
    wc = ((liq_rate - oil_rate) / liq_rate) * 100
    return max(0.0, min(100.0, wc))


def run_dca_forecast(
    start_date: datetime,
    end_date: datetime,
    qi_oil: float,
    di_oil: float,
    b_oil: float,
    qi_liq: float,
    di_liq: float,
    b_liq: float,
    k_month_data: Dict[int, Dict[str, float]],
    use_exponential: bool = True
) -> List[ForecastPoint]:
    """Run DCA forecast with KMonth integration.
    
    Args:
        start_date: Forecast start date
        end_date: Forecast end date
        qi_oil: Initial oil rate (t/day)
        di_oil: Oil decline rate (1/month)
        b_oil: Oil decline exponent
        qi_liq: Initial liquid rate (t/day)
        di_liq: Liquid decline rate (1/month)
        b_liq: Liquid decline exponent
        k_month_data: Dictionary of month_id -> {K_oil, K_liq, K_int, K_inj}
        use_exponential: If True, force exponential decline (ignore b values)
    
    Returns:
        List of ForecastPoint objects
    """
    # Generate monthly date range
    date_range = generate_monthly_dates(start_date, end_date)
    
    if len(date_range) == 0:
        return []
    
    # Calculate days in each month
    days_list = calculate_elapsed_days(date_range)
    
    forecast_points = []
    
    for i, (date, days) in enumerate(zip(date_range, days_list)):
        t = i  # Time in months (0-indexed)
        
        # Get K factors for this month
        month_id = get_month_index(date)
        k_data = k_month_data.get(month_id, {"K_oil": 1.0, "K_liq": 1.0, "K_int": 1.0})
        k_oil = k_data.get("K_oil", 1.0)
        k_liq = k_data.get("K_liq", 1.0)
        
        # Calculate rates using Arps decline
        if use_exponential:
            oil_rate = arps_exponential(qi_oil, di_oil, t)
            liq_rate = arps_exponential(qi_liq, di_liq, t)
        else:
            oil_rate = arps_decline(qi_oil, di_oil, b_oil, t)
            liq_rate = arps_decline(qi_liq, di_liq, b_liq, t)
        
        # Ensure rates are non-negative
        oil_rate = max(0.0, oil_rate)
        liq_rate = max(0.0, liq_rate)
        
        # Calculate cumulative production for the month
        q_oil = calculate_cumulative_production(oil_rate, days, k_oil)
        q_liq = calculate_cumulative_production(liq_rate, days, k_liq)
        
        # Calculate water cut
        wc = calculate_water_cut(oil_rate, liq_rate)
        
        forecast_points.append(ForecastPoint(
            date=date.to_pydatetime(),
            days_in_month=days,
            oil_rate=round(oil_rate, 2),
            liq_rate=round(liq_rate, 2),
            q_oil=round(q_oil, 2),
            q_liq=round(q_liq, 2),
            wc=round(wc, 2)
        ))
    
    return forecast_points


def forecast_to_dict_list(forecast_points: List[ForecastPoint]) -> List[Dict]:
    """Convert forecast points to list of dictionaries for database storage.
    
    Args:
        forecast_points: List of ForecastPoint objects
    
    Returns:
        List of dictionaries with forecast data
    """
    return [
        {
            "date": fp.date.strftime("%Y-%m-%d"),
            "days_in_month": fp.days_in_month,
            "oilRate": fp.oil_rate,
            "liqRate": fp.liq_rate,
            "qOil": fp.q_oil,
            "qLiq": fp.q_liq,
            "wc": fp.wc
        }
        for fp in forecast_points
    ]


# Cumulative production calculation helpers
def calculate_cumulative_totals(forecast_points: List[ForecastPoint]) -> Tuple[float, float]:
    """Calculate total cumulative oil and liquid production.
    
    Args:
        forecast_points: List of ForecastPoint objects
    
    Returns:
        Tuple of (total_oil, total_liquid)
    """
    total_oil = sum(fp.q_oil for fp in forecast_points)
    total_liq = sum(fp.q_liq for fp in forecast_points)
    return total_oil, total_liq


def calculate_eur(
    current_cum: float,
    forecast_points: List[ForecastPoint],
    phase: str = "oil"
) -> float:
    """Calculate Estimated Ultimate Recovery (EUR).
    
    EUR = Current cumulative production + Forecast cumulative production
    
    Args:
        current_cum: Current cumulative production
        forecast_points: List of ForecastPoint objects
        phase: "oil" or "liq"
    
    Returns:
        EUR value
    """
    if phase == "oil":
        forecast_cum = sum(fp.q_oil for fp in forecast_points)
    else:
        forecast_cum = sum(fp.q_liq for fp in forecast_points)
    
    return current_cum + forecast_cum
