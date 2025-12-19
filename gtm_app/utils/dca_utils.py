"""DCA (Decline Curve Analysis) utility functions.

This module provides:
- Arps decline curve functions using daily elapsed time
- Date range generation with pandas (freq="MS")
- KMonth integration for cumulative production calculation
- Elapsed days calculation from start date

Key Formula:
- Exponential: q(t) = qi * exp(-di * 12/365 * t) where t is elapsed days
- Cumulative: Qoil = OilRate * K * days_in_month
"""
import numpy as np
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ArpsParameters:
    """Arps decline curve parameters."""
    qi: float  # Initial rate (t/day)
    di: float  # Decline rate (1/year, typically 0.01-0.5)
    b: float = 0.0  # Decline exponent (0=exponential)


@dataclass
class ForecastPoint:
    """Single forecast data point."""
    date: datetime
    days_in_month: int
    oil_rate: float
    liq_rate: float
    q_oil: float  # Cumulative oil production in month (ton)
    q_liq: float  # Cumulative liquid production in month (ton)
    wc: float     # Water cut percentage


def arps_exponential(qi: float, di: float, t: np.ndarray) -> np.ndarray:
    """Exponential decline using daily elapsed time.
    
    Formula: q(t) = qi * exp(-di * 12/365 * t)
    
    Args:
        qi: Initial rate (t/day)
        di: Decline rate (1/year)
        t: Elapsed time in days (numpy array)
    
    Returns:
        Rate at each time point (numpy array)
    """
    if di <= 0:
        return qi * np.ones_like(t, dtype=float)
    return qi * np.exp(-di * 12 / 365 * t)


def arps_hyperbolic(qi: float, di: float, b: float, t: np.ndarray) -> np.ndarray:
    """Hyperbolic decline using daily elapsed time.
    
    Formula: q(t) = qi / (1 + b * di * 12/365 * t)^(1/b)
    
    Args:
        qi: Initial rate (t/day)
        di: Initial decline rate (1/year)
        b: Decline exponent (0 < b < 1)
        t: Elapsed time in days (numpy array)
    
    Returns:
        Rate at each time point (numpy array)
    """
    if di <= 0 or b <= 0:
        return qi * np.ones_like(t, dtype=float)
    time_factor = di * 12 / 365 * t
    return qi / ((1 + b * time_factor) ** (1 / b))


def arps_harmonic(qi: float, di: float, t: np.ndarray) -> np.ndarray:
    """Harmonic decline using daily elapsed time.
    
    Formula: q(t) = qi / (1 + di * 12/365 * t)
    Special case of hyperbolic where b = 1
    
    Args:
        qi: Initial rate (t/day)
        di: Decline rate (1/year)
        t: Elapsed time in days (numpy array)
    
    Returns:
        Rate at each time point (numpy array)
    """
    if di <= 0:
        return qi * np.ones_like(t, dtype=float)
    return qi / (1 + di * 12 / 365 * t)


def arps_decline(
    qi: float, 
    di: float, 
    b: float, 
    t: np.ndarray
) -> np.ndarray:
    """General Arps decline function that selects appropriate model.
    
    Args:
        qi: Initial rate (t/day)
        di: Decline rate (1/year)
        b: Decline exponent
            - b = 0: Exponential decline
            - 0 < b < 1: Hyperbolic decline
            - b = 1: Harmonic decline
        t: Elapsed time in days (numpy array)
    
    Returns:
        Rate at each time point (numpy array)
    """
    if b == 0 or b < 0.001:  # Exponential
        return arps_exponential(qi, di, t)
    elif abs(b - 1.0) < 0.001:  # Harmonic
        return arps_harmonic(qi, di, t)
    else:  # Hyperbolic
        return arps_hyperbolic(qi, di, b, t)


def generate_forecast_dates(
    start_date: datetime, 
    end_date: datetime
) -> Tuple[List[datetime], np.ndarray, np.ndarray, List[int]]:
    """Generate forecast dates and elapsed days using pandas date_range.
    
    Uses freq="MS" (Month Start) and handles first day properly.
    
    Args:
        start_date: Forecast start date
        end_date: Forecast end date
    
    Returns:
        Tuple of:
        - date_range: List of dates for each period
        - elapsed_days: Array of elapsed days from start (for rate calculation)
        - days_in_month: Array of days in each period
        - month_indices: List of month indices (1-12) for KMonth lookup
    """
    # Generate month start dates
    date_range = pd.date_range(start_date, end_date, freq="MS").to_list()
    
    # If start_date is not 1st of month, insert it at beginning
    first_day = pd.to_datetime(start_date)
    if first_day.day != 1:
        date_range.insert(0, first_day)
    
    if len(date_range) < 2:
        return [], np.array([]), np.array([]), []
    
    # Calculate elapsed days from start
    elapsed_days = np.array([(d - date_range[0]).days for d in date_range])
    
    # Calculate days in each period (difference between consecutive dates)
    days_in_month = elapsed_days[1:] - elapsed_days[:-1]
    
    # Get month index for each period (for KMonth lookup)
    month_indices = [d.month for d in date_range[:-1]]
    
    # Use elapsed_days[:-1] for rate calculation (at start of each period)
    return date_range[:-1], elapsed_days[:-1], days_in_month, month_indices


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
    """Run DCA forecast with KMonth integration using daily elapsed time.
    
    Key formulas:
    - Rate: q(t) = qi * exp(-di * 12/365 * t) for exponential
    - Cumulative: Q = rate * K * days_in_month
    
    Args:
        start_date: Forecast start date
        end_date: Forecast end date
        qi_oil: Initial oil rate (t/day)
        di_oil: Oil decline rate (1/year)
        b_oil: Oil decline exponent
        qi_liq: Initial liquid rate (t/day)
        di_liq: Liquid decline rate (1/year)
        b_liq: Liquid decline exponent
        k_month_data: Dictionary of month_id -> {K_oil, K_liq, K_int, K_inj}
        use_exponential: If True, force exponential decline (ignore b values)
    
    Returns:
        List of ForecastPoint objects
    """
    # Generate dates and elapsed days
    date_range, elapsed_days, days_in_month, month_indices = generate_forecast_dates(
        start_date, end_date
    )
    
    if len(date_range) == 0:
        return []
    
    # Get K factors for each month
    k_oil_array = np.array([
        k_month_data.get(m, {}).get("K_oil", 1.0) 
        for m in month_indices
    ])
    k_liq_array = np.array([
        k_month_data.get(m, {}).get("K_liq", 1.0) 
        for m in month_indices
    ])
    
    # Calculate rates using vectorized Arps decline
    if use_exponential:
        oil_rates = arps_exponential(qi_oil, di_oil, elapsed_days)
        liq_rates = arps_exponential(qi_liq, di_liq, elapsed_days)
    else:
        oil_rates = arps_decline(qi_oil, di_oil, b_oil, elapsed_days)
        liq_rates = arps_decline(qi_liq, di_liq, b_liq, elapsed_days)
    
    # Ensure rates are non-negative
    oil_rates = np.maximum(0.0, oil_rates)
    liq_rates = np.maximum(0.0, liq_rates)
    
    # Calculate cumulative production: Q = rate * K * days_in_month
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


def run_dca_forecast_intervention(
    start_date: datetime,
    end_date: datetime,
    qi_oil: float,
    di_oil: float,
    b_oil: float,
    qi_liq: float,
    di_liq: float,
    b_liq: float,
    k_month_data: Dict[int, Dict[str, float]],
    use_exponential: bool = False  # Intervention uses hyperbolic by default
) -> List[ForecastPoint]:
    """Run DCA forecast for intervention using K_int factor.
    
    Similar to run_dca_forecast but uses K_int instead of K_oil/K_liq.
    
    Args:
        Same as run_dca_forecast
    
    Returns:
        List of ForecastPoint objects
    """
    # Generate dates and elapsed days
    date_range, elapsed_days, days_in_month, month_indices = generate_forecast_dates(
        start_date, end_date
    )
    
    if len(date_range) == 0:
        return []
    
    # Get K_int factors for each month (used for intervention forecast)
    k_int_array = np.array([
        k_month_data.get(m, {}).get("K_int", 1.0) 
        for m in month_indices
    ])
    
    # Calculate rates using vectorized Arps decline
    if use_exponential:
        oil_rates = arps_exponential(qi_oil, di_oil, elapsed_days)
        liq_rates = arps_exponential(qi_liq, di_liq, elapsed_days)
    else:
        oil_rates = arps_decline(qi_oil, di_oil, b_oil, elapsed_days)
        liq_rates = arps_decline(qi_liq, di_liq, b_liq, elapsed_days)
    
    # Ensure rates are non-negative
    oil_rates = np.maximum(0.0, oil_rates)
    liq_rates = np.maximum(0.0, liq_rates)
    
    # Calculate cumulative production using K_int
    q_oil_array = oil_rates * k_int_array * days_in_month
    q_liq_array = liq_rates * k_int_array * days_in_month
    
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


def calculate_cumulative_totals(
    forecast_points: List[ForecastPoint]
) -> Tuple[float, float]:
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