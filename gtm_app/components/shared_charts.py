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


def dual_axis_line_chart(
    data: rx.Var,
    show_oil: rx.Var,
    show_liquid: rx.Var,
    show_wc: rx.Var,
    height: int = 350,
    show_forecast: bool = True,
    show_base_forecast: rx.Var = None,
    intervention_date: rx.Var = None
) -> rx.Component:
    """Create a dual-axis line chart for production data.
    
    Left axis: Production rates (t/day)
    Right axis: Water cut (%)
    
    Args:
        data: Chart data with actual and forecast values
        show_oil: Var for oil visibility
        show_liquid: Var for liquid visibility
        show_wc: Var for water cut visibility
        height: Chart height in pixels
        show_forecast: Whether to show forecast lines
        show_base_forecast: Optional var for base forecast visibility
        intervention_date: Optional intervention date for vertical line
        
    Returns:
        Composed chart component
    """
    chart_elements = []
    
    # Actual oil rate (left Y-axis)
    chart_elements.append(
        rx.cond(
            show_oil,
            rx.recharts.line(
                data_key="oilRate",
                name="Oil Rate (Actual)",
                stroke=rx.color("green", 9),
                dot=True,
                type_="monotone",
                connect_nulls=True,
                stroke_width=2,
                y_axis_id="left",
            ),
            rx.fragment(),
        )
    )
    
    # Actual liquid rate (left Y-axis)
    chart_elements.append(
        rx.cond(
            show_liquid,
            rx.recharts.line(
                data_key="liqRate",
                name="Liq Rate (Actual)",
                stroke=rx.color("blue", 9),
                dot=True,
                type_="monotone",
                connect_nulls=True,
                stroke_width=2,
                y_axis_id="left",
            ),
            rx.fragment(),
        )
    )
    
    # Forecast lines
    if show_forecast:
        # Forecast oil rate
        chart_elements.append(
            rx.cond(
                show_oil,
                rx.recharts.line(
                    data_key="oilRateForecast",
                    name="Oil Rate (Forecast)",
                    stroke=rx.color("green", 10),
                    stroke_dasharray="5 5",
                    dot=False,
                    type_="monotone",
                    connect_nulls=True,
                    stroke_width=2,
                    y_axis_id="left",
                ),
                rx.fragment(),
            )
        )
        
        # Forecast liquid rate
        chart_elements.append(
            rx.cond(
                show_liquid,
                rx.recharts.line(
                    data_key="liqRateForecast",
                    name="Liq Rate (Forecast)",
                    stroke=rx.color("blue", 10),
                    stroke_dasharray="5 5",
                    dot=False,
                    type_="monotone",
                    connect_nulls=True,
                    stroke_width=2,
                    y_axis_id="left",
                ),
                rx.fragment(),
            )
        )
    
    # Base forecast lines (for intervention comparison)
    if show_base_forecast is not None:
        # Base oil rate
        chart_elements.append(
            rx.cond(
                show_oil & show_base_forecast,
                rx.recharts.line(
                    data_key="oilRateBase",
                    name="Oil Rate (Base/No GTM)",
                    stroke=rx.color("green", 6),
                    stroke_dasharray="2 4",
                    dot=False,
                    type_="monotone",
                    connect_nulls=True,
                    stroke_width=2,
                    y_axis_id="left",
                ),
                rx.fragment(),
            )
        )
        
        # Base liquid rate
        chart_elements.append(
            rx.cond(
                show_liquid & show_base_forecast,
                rx.recharts.line(
                    data_key="liqRateBase",
                    name="Liq Rate (Base/No GTM)",
                    stroke=rx.color("blue", 6),
                    stroke_dasharray="2 4",
                    dot=False,
                    type_="monotone",
                    connect_nulls=True,
                    stroke_width=2,
                    y_axis_id="left",
                ),
                rx.fragment(),
            )
        )
    
    # Water Cut (right Y-axis)
    chart_elements.append(
        rx.cond(
            show_wc,
            rx.recharts.line(
                data_key="wc",
                name="Water Cut (%)",
                stroke=rx.color("red", 9),
                dot=True,
                type_="monotone",
                connect_nulls=True,
                stroke_width=2,
                y_axis_id="right",
            ),
            rx.fragment(),
        )
    )
    
    # Water Cut Forecast
    if show_forecast:
        chart_elements.append(
            rx.cond(
                show_wc,
                rx.recharts.line(
                    data_key="wcForecast",
                    name="WC Forecast (%)",
                    stroke=rx.color("red", 10),
                    stroke_dasharray="5 5",
                    dot=False,
                    type_="monotone",
                    connect_nulls=True,
                    stroke_width=2,
                    y_axis_id="right",
                ),
                rx.fragment(),
            )
        )
    
    # Base Water Cut
    if show_base_forecast is not None:
        chart_elements.append(
            rx.cond(
                show_wc & show_base_forecast,
                rx.recharts.line(
                    data_key="wcBase",
                    name="WC Base (%)",
                    stroke=rx.color("red", 6),
                    stroke_dasharray="2 4",
                    dot=False,
                    type_="monotone",
                    connect_nulls=True,
                    stroke_width=2,
                    y_axis_id="right",
                ),
                rx.fragment(),
            )
        )
    
    # Intervention vertical line
    if intervention_date is not None:
        chart_elements.append(
            rx.recharts.reference_line(
                x=intervention_date,
                stroke=rx.color("orange", 9),
                stroke_dasharray="3 3",
                label="GTM",
                stroke_width=2,
            )
        )
    
    # Add axes and grid
    chart_elements.extend([
        rx.recharts.x_axis(
            data_key="date",
            angle=-45,
            text_anchor="end",
            height=80,
            tick={"fontSize": 11}
        ),
        rx.recharts.y_axis(
            y_axis_id="left",
            orientation="left",
            label={"value": "Rate (t/day)", "angle": -90, "position": "insideLeft", "offset": 10},
            tick={"fontSize": 11},
            stroke=rx.color("gray", 9),
        ),
        rx.recharts.y_axis(
            y_axis_id="right",
            orientation="right",
            label={"value": "Water Cut (%)", "angle": 90, "position": "insideRight", "offset": 10},
            tick={"fontSize": 11},
            domain=[0, 100],
            stroke=rx.color("red", 9),
        ),
        rx.recharts.cartesian_grid(stroke_dasharray="3 3"),
        rx.recharts.graphing_tooltip(),
        rx.recharts.legend(icon_size=5),
    ])
    
    return rx.recharts.composed_chart(
        *chart_elements,
        data=data,
        width="100%",
        height=height,
        margin={"bottom": 10, "left": 20, "right": 60, "top": 10},
    )


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


def bar_chart_simple(
    data: rx.Var,
    data_key: str = "value",
    name_key: str = "name",
    height: int = 200,
    color_scheme: str = "accent"
) -> rx.Component:
    """Create a simple bar chart.
    
    Args:
        data: Chart data
        data_key: Key for bar values
        name_key: Key for x-axis labels
        height: Chart height
        color_scheme: Color scheme for bars
        
    Returns:
        Bar chart component
    """
    return rx.recharts.bar_chart(
        rx.recharts.bar(
            data_key=data_key,
            stroke=rx.color(color_scheme, 9),
            fill=rx.color(color_scheme, 8),
        ),
        rx.recharts.x_axis(data_key=name_key),
        rx.recharts.y_axis(),
        rx.recharts.graphing_tooltip(),
        data=data,
        width="100%",
        height=height,
    )