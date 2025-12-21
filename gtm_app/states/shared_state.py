"""Shared base state with common functionality for Production and GTM states."""
import reflex as rx
from typing import Dict, List, Optional
from datetime import datetime

from ..services.dca_service import DCAService
from ..services.database_service import DatabaseService


class SharedForecastState(rx.State):
    """Shared state for forecast-related functionality.
    
    This base state provides common functionality used by both
    ProductionState and GTMState, reducing code duplication.
    """
    
    # KMonth data cache (shared across states)
    k_month_data: Dict[int, Dict[str, float]] = {}
    k_month_loaded: bool = False
    
    # Common production history data
    history_prod: List[Dict] = []
    
    # Common forecast data
    forecast_data: List[Dict] = []
    
    # Common chart data
    chart_data: List[Dict] = []
    
    # Phase display toggles
    show_oil: bool = True
    show_liquid: bool = True
    show_wc: bool = True
    
    # Common forecast parameters
    forecast_end_date: str = ""
    current_forecast_version: int = 0
    available_forecast_versions: List[int] = []
    
    # Loading states
    is_loading: bool = False
    
    # DCA mode (True=Exponential, False=Hyperbolic)
    use_exponential_dca: bool = True
    
    def toggle_oil(self, checked: bool):
        """Toggle oil rate visibility."""
        self.show_oil = checked
    
    def toggle_liquid(self, checked: bool):
        """Toggle liquid rate visibility."""
        self.show_liquid = checked
    
    def toggle_wc(self, checked: bool):
        """Toggle water cut visibility."""
        self.show_wc = checked
    
    def set_forecast_end_date(self, date: str):
        """Set the forecast end date."""
        self.forecast_end_date = date
    
    def set_dca_mode(self, use_exponential: bool):
        """Toggle between Exponential and Hyperbolic DCA."""
        self.use_exponential_dca = use_exponential
    
    def _load_k_month_data(self):
        """Load KMonth data from database and cache it."""
        if self.k_month_loaded and self.k_month_data:
            return
        
        try:
            with rx.session() as session:
                self.k_month_data = DCAService.load_k_month_data(session)
                self.k_month_loaded = True
        except Exception as e:
            print(f"Error loading KMonth data: {e}")
            self.k_month_data = DCAService.DEFAULT_K_MONTH.copy()
            self.k_month_loaded = True
    
    def _update_chart_data(self, base_forecast_data: List[Dict] = None):
        """Update chart data combining actual and forecast data.
        
        Args:
            base_forecast_data: Optional base case forecast for comparison
        """
        self.chart_data = DCAService.build_chart_data(
            history_prod=self.history_prod,
            forecast_data=self.forecast_data,
            base_forecast_data=base_forecast_data
        )
    
    def _format_history_for_table(self, max_records: int = 24) -> List[Dict]:
        """Format history data for table display.
        
        Args:
            max_records: Maximum records to return
            
        Returns:
            Formatted list of dictionaries
        """
        sorted_data = sorted(
            self.history_prod,
            key=lambda x: x["Date"],
            reverse=True
        )[:max_records]
        
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
    
    def _format_forecast_for_table(self, max_records: int = 24) -> List[Dict]:
        """Format forecast data for table display.
        
        Args:
            max_records: Maximum records to return
            
        Returns:
            Formatted list of dictionaries
        """
        return [
            {
                "Date": f["date"],
                "OilRate": f"{f['oilRate']:.1f}",
                "LiqRate": f"{f['liqRate']:.1f}",
                "WC": f"{f.get('wc', 0):.1f}",
                "WC_val": f.get('wc', 0),
                "Qoil": f"{f.get('qOil', 0):.0f}",
                "Qliq": f"{f.get('qLiq', 0):.0f}"
            }
            for f in self.forecast_data[:max_records]
        ]
    
    # ========== Common Computed Properties ==========
    
    @rx.var
    def history_record_count(self) -> int:
        """Get count of history records."""
        return len(self.history_prod)
    
    @rx.var
    def date_range_display(self) -> str:
        """Display date range of history data."""
        if not self.history_prod:
            return "No data"
        
        dates = [p["Date"] for p in self.history_prod]
        min_date = min(dates)
        max_date = max(dates)
        
        min_str = min_date.strftime("%Y-%m-%d") if isinstance(min_date, datetime) else str(min_date)
        max_str = max_date.strftime("%Y-%m-%d") if isinstance(max_date, datetime) else str(max_date)
        
        return f"{min_str} to {max_str}"
    
    @rx.var
    def forecast_totals_display(self) -> str:
        """Display total cumulative production from forecast."""
        if not self.forecast_data:
            return "No forecast"
        total_qoil = sum(f.get("qOil", 0) for f in self.forecast_data)
        total_qliq = sum(f.get("qLiq", 0) for f in self.forecast_data)
        return f"Total: Qoil={total_qoil:.0f}t | Qliq={total_qliq:.0f}t"
    
    @rx.var
    def forecast_version_options(self) -> List[str]:
        """Get version options for dropdown."""
        return [f"v{v}" for v in self.available_forecast_versions]
    
    @rx.var
    def current_version_display(self) -> str:
        """Display current version string."""
        return f"v{self.current_forecast_version}" if self.current_forecast_version > 0 else ""
    
    @rx.var
    def is_k_month_loaded(self) -> bool:
        """Check if KMonth data is loaded."""
        return self.k_month_loaded and len(self.k_month_data) > 0