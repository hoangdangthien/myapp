"""Shared chart components for Production and GTM pages.

These components provide consistent chart styling and behavior
across the application using Recharts.
"""
import reflex as rx
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

def chart_legend() -> rx.Component:
    """Create a chart legend showing line styles.
    
    Returns:
        Legend component
    """
    return rx.hstack(
        rx.badge(
            rx.hstack(
                rx.box(width="12px", height="3px", bg=rx.color("green", 9)),
                rx.text("Oil (Actual)", size="1"),
                spacing="1",
            ),
            variant="soft",
        ),
        rx.badge(
            rx.hstack(
                rx.box(width="12px", height="3px", bg=rx.color("blue", 9)),
                rx.text("Liquid (Actual)", size="1"),
                spacing="1",
            ),
            variant="soft",
        ),
        rx.badge(
            rx.hstack(
                rx.box(width="12px", height="3px", bg=rx.color("red", 9)),
                rx.text("Water Cut (%)", size="1"),
                spacing="1",
            ),
            variant="soft",
        ),
        rx.badge(
            rx.hstack(
                rx.box(
                    width="12px",
                    height="3px",
                    bg=rx.color("gray", 6),
                    style={"border_top": "2px dashed"}
                ),
                rx.text("Forecast", size="1"),
                spacing="1",
            ),
            variant="soft",
        ),
        spacing="2",
        justify="center",
    )


def production_chart_card(
    title: str,
    chart_component: rx.Component,
    toggle_controls: rx.Component,
    show_legend: bool = True
) -> rx.Component:
    """Create a card wrapper for production charts.
    
    Args:
        title: Chart title
        chart_component: The chart to display
        toggle_controls: Toggle controls component
        show_legend: Whether to show the legend
        
    Returns:
        Card-wrapped chart component
    """
    content = [
        rx.hstack(
            rx.heading(title, size="4"),
            rx.spacer(),
            toggle_controls,
            width="100%",
            align="center",
        ),
        chart_component,
    ]
    
    if show_legend:
        content.append(chart_legend())
    
    return rx.card(
        rx.vstack(
            *content,
            width="100%",
            align="center",
            spacing="3",
        ),
        padding="1em",
        width="100%",
    )


def dual_axis_line_chart(
    fig: rx.Var,  # Now accepts a Plotly figure variable
) -> rx.Component:
    """Render a dual-axis production chart using Plotly."""
    return rx.plotly(
        data=fig,
        width="100%",
        config={"displayModeBar": False},
        height="400px"
    )

def bar_chart_simple(
    fig: rx.Var,  # Now accepts a Plotly figure variable
) -> rx.Component:
    """Render a simple bar chart using Plotly."""
    return rx.plotly(
        data=fig,
        width="100%",
        config={"displayModeBar": False}
    )
