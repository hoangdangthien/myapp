"""Shared base state with common functionality for Production and GTM states."""
import reflex as rx
from typing import Dict, List, Optional
from datetime import datetime
import plotly.graph_objects as go

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
    show_base_forecast: bool = True  # Default to True so base forecast shows
    
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
        
    def toggle_base_forecast(self, checked: bool):
        """Toggle base forecast visibility."""
        self.show_base_forecast = checked
    
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

    @rx.var
    def plotly_dual_axis_chart(self) -> go.Figure:
        """Generate a dual-axis Plotly figure from chart_data.
        
        This chart displays:
        - Actual production data (solid lines with markers)
        - Intervention/Production forecast (dashed lines)
        - Base forecast without intervention (dotted lines) - toggled by show_base_forecast
        - Water Cut on secondary Y-axis
        - Intervention date vertical line (if available)
        """
        if not self.chart_data:
            return go.Figure()

        fig = go.Figure()
        
        # Extract dates from chart data
        dates = [d.get("date") for d in self.chart_data]
        
        # 1. Oil Rate Traces
        if self.show_oil:
            # Actual oil rate
            fig.add_trace(go.Scatter(
                x=dates, 
                y=[d.get("oilRate") for d in self.chart_data],
                name="Oil Rate (Actual)", 
                mode="lines+markers",
                line=dict(color="#10b981", width=2), 
                marker=dict(size=4),
                connectgaps=True
            ))
            # Forecast oil rate
            fig.add_trace(go.Scatter(
                x=dates, 
                y=[d.get("oilRateForecast") for d in self.chart_data],
                name="Oil Forecast", 
                mode="lines",
                line=dict(color="#059669", width=2, dash="dash"), 
                connectgaps=True
            ))
            # Base forecast oil rate (No GTM) - only show if toggled and data exists
            if self.show_base_forecast:
                oil_base_values = [d.get("oilRateBase") for d in self.chart_data]
                # Only add trace if there's actual base data (not all None)
                if any(v is not None for v in oil_base_values):
                    fig.add_trace(go.Scatter(
                        x=dates, 
                        y=oil_base_values,
                        name="Base Oil (No GTM)", 
                        mode="lines",
                        line=dict(color="#6ee7b7", width=2, dash="dot"), 
                        connectgaps=True
                    ))

        # 2. Liquid Rate Traces
        if self.show_liquid:
            # Actual liquid rate
            fig.add_trace(go.Scatter(
                x=dates, 
                y=[d.get("liqRate") for d in self.chart_data],
                name="Liq Rate (Actual)", 
                mode="lines+markers",
                line=dict(color="#3b82f6", width=2),
                marker=dict(size=4),
                connectgaps=True
            ))
            # Forecast liquid rate
            fig.add_trace(go.Scatter(
                x=dates, 
                y=[d.get("liqRateForecast") for d in self.chart_data],
                name="Liq Forecast", 
                mode="lines",
                line=dict(color="#2563eb", width=2, dash="dash"), 
                connectgaps=True
            ))
            # Base forecast liquid rate (No GTM)
            if self.show_base_forecast:
                liq_base_values = [d.get("liqRateBase") for d in self.chart_data]
                if any(v is not None for v in liq_base_values):
                    fig.add_trace(go.Scatter(
                        x=dates, 
                        y=liq_base_values,
                        name="Base Liq (No GTM)", 
                        mode="lines",
                        line=dict(color="#93c5fd", width=2, dash="dot"), 
                        connectgaps=True
                    ))

        # 3. Water Cut Traces (Secondary Y-Axis)
        if self.show_wc:
            # Actual water cut
            fig.add_trace(go.Scatter(
                x=dates, 
                y=[d.get("wc") for d in self.chart_data],
                name="Water Cut", 
                mode="lines+markers",
                line=dict(color="#ef4444", width=2),
                marker=dict(size=4),
                yaxis="y2", 
                connectgaps=True
            ))
            # Forecast water cut
            fig.add_trace(go.Scatter(
                x=dates, 
                y=[d.get("wcForecast") for d in self.chart_data],
                name="WC Forecast", 
                mode="lines",
                line=dict(color="#dc2626", width=2, dash="dash"),
                yaxis="y2", 
                connectgaps=True
            ))
            # Base forecast water cut (No GTM)
            if self.show_base_forecast:
                wc_base_values = [d.get("wcBase") for d in self.chart_data]
                if any(v is not None for v in wc_base_values):
                    fig.add_trace(go.Scatter(
                        x=dates, 
                        y=wc_base_values,
                        name="Base WC (No GTM)", 
                        mode="lines",
                        line=dict(color="#fca5a5", width=2, dash="dot"),
                        yaxis="y2", 
                        connectgaps=True
                    ))

        # 4. Intervention Vertical Line (if intervention_date exists in subclass)
        int_date = getattr(self, "intervention_date", None)
        if int_date and int_date.strip():
            fig.add_vline(
                x=int_date, 
                line_width=2, 
                line_dash="dash", 
                line_color="#f59e0b", 
                annotation_text="GTM",
                annotation_position="top"
            )

        # Layout Configuration
        fig.update_layout(
            xaxis=dict(
                title="Date", 
                showgrid=True, 
                gridcolor="rgba(0,0,0,0.1)"
            ),
            yaxis=dict(
                title="Rate (t/day)", 
                side="left", 
                showgrid=True, 
                gridcolor="rgba(0,0,0,0.1)"
            ),
            yaxis2=dict(
                title="Water Cut (%)", 
                side="right", 
                overlaying="y", 
                range=[0, 100], 
                showgrid=False
            ),
            legend=dict(
                orientation="h", 
                yanchor="bottom", 
                y=1.02, 
                xanchor="right", 
                x=1, 
                font=dict(size=10)
            ),
            hovermode="x unified",
            margin=dict(l=50, r=50, t=30, b=50),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=400,
        )
        return fig