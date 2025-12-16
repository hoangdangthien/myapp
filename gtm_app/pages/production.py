"""Production monitoring page with MSSQL Server integration."""
import reflex as rx
from ..templates.template import template
from ..states.base_state import BaseState
from ..components.production_components import (
    connection_dialog,
    filter_controls,
    master_table,
    stats_summary,
)


@template(
    route="/",
    title="Production | GTM Dashboard",
    description="Production monitoring and well master data",
    on_load=BaseState.load_master_data,
)
def production_page() -> rx.Component:
    """Production monitoring page with Master table from MSSQL Server.
    
    Features:
    - Connect to external MSSQL Server database (OFM)
    - Display Master table with well information
    - Filter and search capabilities
    - Connection status monitoring
    """
    return rx.vstack(
        # Page Header
        rx.hstack(
            rx.vstack(
                rx.heading("Production Monitoring", size="7"),
                align="center",
                spacing="1",
            ),
            rx.spacer(),
            rx.hstack(
                connection_dialog(),
                rx.button(
                    rx.icon("refresh-cw", size=16),
                    rx.text("Refresh", size="2"),
                    on_click=BaseState.load_master_data,
                    size="2",
                ),
                spacing="2",
            ),
            width="100%",
            align="center",
        ),
        rx.divider(),
        
        # Statistics Summary
        stats_summary(),
        
        # Master Table Section
        rx.card(
            rx.vstack(
                # Table Header with Controls
                rx.hstack(
                    rx.heading("Master Table", size="5"),
                    rx.spacer(),
                    filter_controls(),
                    width="100%",
                    align="center",
                ),
                rx.divider(),
                
                # Master Table
                rx.cond(
                    BaseState.total_wells > 0,
                    master_table(),
                    rx.vstack(
                        rx.icon("database", size=48, color=rx.color("gray", 8)),
                        rx.text(
                            "No data available",
                            size="4",
                            color=rx.color("gray", 10),
                        ),
                        rx.text(
                            "Click 'Refresh' to load data from MSSQL Server",
                            size="2",
                            color=rx.color("gray", 9),
                        ),
                        align="center",
                        spacing="2",
                        padding="3em",
                    ),
                ),
                
                spacing="3",
                width="100%",
            ),
            padding="1.5em",
            width="100%",
        ),
        
        # Future Production Analytics Placeholder
        rx.card(
            rx.vstack(
                rx.hstack(
                    rx.icon("trending-up", size=20, color=rx.color("gray", 9)),
                    rx.heading("Production Analytics", size="4"),
                    rx.badge("Coming Soon", color_scheme="blue", size="2"),
                    spacing="2",
                ),
                rx.text(
                    "Future features: Production rate monitoring, decline curve analysis, "
                    "forecasting, and field-level aggregation",
                    color=rx.color("gray", 10),
                    size="2",
                ),
                spacing="2",
                padding="2em",
                align="center",
            ),
            width="100%",
        ),
        
        align="start",
        spacing="4",
        width="100%",
    )