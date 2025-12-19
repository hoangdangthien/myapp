"""Production monitoring page with CompletionID data and DCA forecasting."""
import reflex as rx
from ..templates.template import template
from ..states.production_state import ProductionState
from ..components.production_components import (
    completion_filter_controls,
    completion_table,
    completion_stats_summary,
    selected_completion_info,
)
from ..components.production_tables import (
    forecast_controls,
    production_history_table,
    forecast_result_table,
    production_rate_chart,
)


def completion_table_section() -> rx.Component:
    """Left section: CompletionID table with controls."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.heading("Completion ID", size="4"),
                rx.spacer(),
                completion_filter_controls(),
                width="100%",
                align="center",
            ),
            rx.divider(),
            completion_table(),
            width="100%",
            spacing="3",
        ),
        padding="1em",
        height="100%",
    )


def forecast_section() -> rx.Component:
    """Right section: Forecast controls and results."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.heading("Production Forecast (Exponential DCA)", size="4"),
                rx.spacer(),
                forecast_controls(),
                width="100%",
                align="center",
            ),
            rx.divider(),
            
            # Selected completion info
            selected_completion_info(),
            
            # Two tables side by side
            rx.grid(
                # Production History
                rx.vstack(
                    rx.badge("Production History (Last 5 Years)", color_scheme="green", size="2"),
                    production_history_table(),
                    width="100%",
                    spacing="2",
                ),
                # Forecast Results
                rx.vstack(
                    rx.cond(
                        ProductionState.current_forecast_version > 0,
                        rx.badge(
                            f"Forecast Results v{ProductionState.current_forecast_version}",
                            color_scheme="blue",
                            size="2"
                        ),
                        rx.badge("No Forecast", color_scheme="gray", size="2"),
                    ),
                    forecast_result_table(),
                    width="100%",
                    spacing="2",
                ),
                columns="2",
                spacing="3",
                width="100%",
            ),
            
            width="100%",
            spacing="3",
        ),
        padding="1em",
        height="100%",
    )


@template(
    route="/",
    title="Production | GTM Dashboard",
    description="Production monitoring and DCA forecasting",
    on_load=ProductionState.load_completions,
)
def production_page() -> rx.Component:
    """Production monitoring page with CompletionID data and DCA forecasting.
    
    Features:
    - Display CompletionID table with well completion information
    - Load HistoryProd data (last 5 years) for selected completion
    - Run Exponential DCA forecast: q(t) = qi * exp(-Di * t)
      - qi: Last rate from HistoryProd
      - Di: Decline rate from CompletionID.Do/Dl
    - Uses KMonth table for uptime factors
    - Cumulative: Qoil = K_oil * days_in_month * OilRate
    - Save forecasts to ProductionForecast table (max 4 versions, FIFO)
    - If UniqueId has planned intervention in InterventionID,
      also save forecast to InterventionForecast as version 0
    
    DCA Formula: q(t) = qi * exp(-Di * t)
    Cumulative: Q = K * days_in_month * rate
    """
    return rx.vstack(
        # Page Header
        rx.hstack(
            rx.vstack(
                rx.heading("Production Monitoring", size="6"),
                rx.text(
                    "Exponential Decline Curve Analysis (DCA) with KMonth Integration",
                    size="2",
                    color=rx.color("gray", 10)
                ),
                spacing="1",
                align="start",
            ),
            rx.spacer(),
            rx.hstack(
                rx.button(
                    rx.icon("refresh-cw", size=16),
                    rx.text("Refresh", size="2"),
                    on_click=ProductionState.load_completions,
                    size="2",
                    variant="soft",
                ),
                spacing="2",
            ),
            width="100%",
            align="center",
        ),
        rx.divider(),
        
        # Statistics Summary
        completion_stats_summary(),
        
        # Main content: Two columns
        rx.grid(
            # Left: CompletionID Table
            completion_table_section(),
            # Right: Forecast Section
            forecast_section(),
            columns="2",
            spacing="4",
            width="100%",
        ),
        
        # Production Rate Chart (full width)
        production_rate_chart(),
        
        # DCA Formula Reference
        rx.card(
            rx.hstack(
                rx.icon("info", size=16, color=rx.color("blue", 9)),
                rx.vstack(
                    rx.text("Exponential Decline Curve Analysis with KMonth", weight="bold", size="2"),
                    rx.text(
                        "Formula: q(t) = qi × exp(-Di × t) | "
                        "Cumulative: Q = K × days × rate | "
                        "K factors from KMonth table per month | "
                        "Dates generated with pandas date_range(freq='MS')",
                        size="1",
                        color=rx.color("gray", 10)
                    ),
                    spacing="0",
                    align="start",
                ),
                spacing="2",
                width="100%",
            ),
            padding="0.75em",
            variant="surface",
        ),
        
        align="start",
        spacing="4",
        width="100%",
    )