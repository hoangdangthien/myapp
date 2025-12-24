import reflex as rx
from ..states.gtm_state import *
from ..states.production_state import *
from typing import List, Dict, Callable, Optional

def chart_toggle_controls(
    show_oil: rx.Var,
    show_liquid: rx.Var,
    show_wc: rx.Var,
    toggle_oil: Callable,
    toggle_liquid: Callable,
    toggle_wc: Callable,
    show_base_forecast: rx.Var = None,
    toggle_base_forecast: Callable = None
) -> rx.Component:
    """Create chart display toggle controls.
    
    Args:
        show_oil: Var for oil visibility
        show_liquid: Var for liquid visibility
        show_wc: Var for water cut visibility
        toggle_oil: Callback for oil toggle
        toggle_liquid: Callback for liquid toggle
        toggle_wc: Callback for water cut toggle
        show_base_forecast: Optional var for base forecast visibility
        toggle_base_forecast: Optional callback for base forecast toggle
        
    Returns:
        Toggle controls component
    """
    controls = [
        rx.text("Show:", size="2", weight="bold"),
        rx.checkbox(
            "Oil",
            checked=show_oil,
            on_change=toggle_oil,
            color_scheme="green",
        ),
        rx.checkbox(
            "Liquid",
            checked=show_liquid,
            on_change=toggle_liquid,
            color_scheme="blue",
        ),
        rx.checkbox(
            "Water Cut",
            checked=show_wc,
            on_change=toggle_wc,
            color_scheme="red",
        ),
    ]
    
    # Add base forecast toggle if provided
    if show_base_forecast is not None and toggle_base_forecast is not None:
        controls.append(
            rx.checkbox(
                "Base Forecast",
                checked=show_base_forecast,
                on_change=toggle_base_forecast,
                color_scheme="gray",
            )
        )
    
    return rx.hstack(*controls, spacing="3", align="center")

def production_rate_chart(state:rx.State) -> rx.Component:
    """Line chart showing rate vs time with intervention line, base forecast, and Water Cut.
    
    Chart includes:
    - Actual production data (solid lines)
    - Intervention forecast (dashed lines) - versions 1,2,3
    - Base forecast (dotted lines) - version 0 (without intervention)
    - Water Cut on secondary Y-axis
    - Intervention date vertical reference line
    
    """
    toggle_controls = chart_toggle_controls(
        show_oil=state.show_oil,
        show_liquid=state.show_liquid,
        show_wc=state.show_wc,
        toggle_oil=state.toggle_oil,
        toggle_liquid=state.toggle_liquid,
        toggle_wc=state.toggle_wc,
        show_base_forecast=state.show_base_forecast,
        toggle_base_forecast=state.toggle_base_forecast,
    )
    chart = rx.plotly(
        data=state.plotly_dual_axis_chart,
        width="100%",
        config={"displayModeBar": False},
        height="400px")
    
    # Custom card with base forecast status indicator
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.heading("Production Rate vs Time", size="4"),
                rx.spacer(),
                # Base forecast status badge
                toggle_controls,
                width="100%",
                align="center",
            ),
            chart,
            # Legend for line styles
            rx.hstack(
                rx.badge(
                    rx.hstack(
                        rx.box(width="16px", height="3px", bg="#10b981"),
                        rx.text("Actual", size="1"),
                        spacing="1",
                    ),
                    variant="soft",
                    size="1",
                ),
                rx.badge(
                    rx.hstack(
                        rx.box(
                            width="16px", 
                            height="3px", 
                            style={"border_top": "2px dashed #059669"}
                        ),
                        rx.text("Forecast", size="1"),
                        spacing="1",
                    ),
                    variant="soft",
                    size="1",
                ),
                rx.cond(
                    state.has_base_forecast,
                    rx.badge(
                        rx.hstack(
                            rx.box(
                                width="16px", 
                                height="3px", 
                                style={"border_top": "2px dotted #6ee7b7"}
                            ),
                            rx.text("Base (No GTM)", size="1"),
                            spacing="1",
                        ),
                        variant="soft",
                        size="1",
                    ),
                    rx.fragment(),
                ),
                spacing="2",
                justify="center",
            ),
            width="100%",
            align="center",
            spacing="3",
        ),
        padding="1em",
        width="100%",
    ) 

