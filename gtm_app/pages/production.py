"""Production monitoring page with CompletionID data and DCA forecasting.

Updated to include Dip/Dir columns and filter by reservoir.
"""
import reflex as rx
from ..templates.template import template
from ..states.production_state import ProductionState
from ..components.production_components import (
    completion_filter_controls,
    completion_table,
    forecast_version_selector,
    batch_update_dip_dialog,
    batch_update_dir_dialog,
)
from ..components.production_tables import (
    forecast_controls,
    forecast_result_table,
    production_rate_chart,
)
from ..components.tables import *


def completion_table_section() -> rx.Component:
    """Left section: CompletionID table with controls and batch update buttons."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.heading("Completion ID", size="4"),
                rx.spacer(),
                rx.hstack(
                    batch_update_dip_dialog(),
                    batch_update_dir_dialog(),
                    completion_filter_controls(),
                    spacing="2",
                    wrap="wrap",
                ),
                width="100%",
                align="center",
                wrap="wrap",
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
                rx.heading("Production Forecast", size="4"),
                rx.spacer(),
                forecast_controls(),
                width="100%",
                align="center",
            ),
            rx.divider(),
            
            # Two tables side by side
            rx.grid(
                # Production History
                rx.vstack(
                    rx.badge("Production History (Last 5 Years)", color_scheme="green", size="2"),
                    production_table(ProductionState.production_table_data),
                    width="100%",
                    spacing="2",
                ),
                # Forecast Results
                rx.vstack(
                    rx.hstack(
                    forecast_version_selector(),
                    rx.cond(
                        ProductionState.current_forecast_version > 0,
                        rx.button(
                            rx.icon("trash-2", size=14),
                            rx.text("Delete version", size="1"),
                            color_scheme="red",
                            size="1",
                            on_click=ProductionState.delete_current_forecast_version,
                            
                            ),
                        rx.fragment(),
                        ),
                        align="center"
                    ),
                    production_table(ProductionState.forecast_table_data),
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
    title="Production | Production Dashboard",
    description="Production monitoring and DCA forecasting",
    on_load=ProductionState.load_completions,
)
def production_page() -> rx.Component:
    """Production monitoring page with CompletionID data and DCA forecasting.
    
    Features:
    - Display CompletionID table with well completion information
    - Dip (Platform adjustment) and Dir (Reservoir+Field adjustment) columns
    - Filter by reservoir
    - Load HistoryProd data (last 5 years) for selected completion
    - Run Exponential DCA forecast: q(t) = qi * exp(-Di_eff * t)
      - qi: Last rate from HistoryProd
      - Di_eff: Effective decline = Do * (1 + Dip) * (1 + Dir)
    - Uses KMonth table for uptime factors
    - Cumulative: Qoil = K_oil * days_in_month * OilRate
    - Save forecasts to ProductionForecast table (max 4 versions, FIFO)
    - Batch update Dip for all completions on a platform
    - Batch update Dir for all completions in a reservoir+field
    
    DCA Formula: q(t) = qi * exp(-Di_eff * 12/365 * t)
    Effective Decline: Di_eff = Do * (1 + Dip) * (1 + Dir)
    """
    return rx.vstack(
        # Page Header
        rx.hstack(
            rx.vstack(
                rx.heading("Production Management", size="6"),
                spacing="1",
                align="start",
            ),
            rx.spacer(),
            rx.hstack(
                rx.badge(f"Total Completions: {ProductionState.total_completions}", color_scheme="blue",size="2"),
                rx.button(
                    rx.icon("refresh-cw", size=14),
                    rx.text("Reload", size="2"),
                    on_click=ProductionState.load_completions,
                    size="1",
                    variant="soft",
                ),
                spacing="2",
            ),
            width="100%",
            align="center",
        ),
        rx.divider(),
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
        align="start",
        spacing="4",
        width="100%",
    )