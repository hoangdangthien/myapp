"""Chart and visualization components for Intervention data."""
import reflex as rx
from ..states.gtm_state import GTMState


def stats_card(
    title: str, 
    value: rx.Var, 
    icon: str,
    color_scheme: str = "accent"
) -> rx.Component:
    """Create a statistics card component."""
    return rx.card(
        rx.hstack(
            rx.vstack(
                rx.text(title, size="1", color=rx.color("gray", 11)),
                rx.heading(value, size="5"),
                align="start",
                spacing="1",
            ),
            rx.spacer(),
            rx.box(
                rx.icon(icon, size=20, color=rx.color(color_scheme, 9)),
                padding="0.5em",
                background=rx.color(color_scheme, 3),
                border_radius="6px",
            ),
            width="100%",
        ),
        padding="1em",
    )


def stats_cards() -> rx.Component:
    """Create the statistics cards section."""
    return rx.grid(
        stats_card("Total", GTMState.total_interventions, "layers", "blue"),
        stats_card("Planned", GTMState.planned_interventions, "calendar", "yellow"),
        stats_card("Completed", GTMState.completed_interventions, "check-circle", "green"),
        columns="3",
        spacing="3",
        width="100%",
    )


def gtm_type_chart() -> rx.Component:
    """Bar chart showing GTM type distribution."""
    return rx.card(
        rx.vstack(
            rx.heading("Intervention Types", size="4"),
            rx.recharts.bar_chart(
                rx.recharts.bar(
                    data_key="value",
                    stroke=rx.color("accent", 9),
                    fill=rx.color("accent", 8),
                ),
                rx.recharts.x_axis(data_key="name"),
                rx.recharts.y_axis(),
                rx.recharts.graphing_tooltip(),
                data=GTMState.gtms_for_graph,
                width="100%",
                height=200,
            ),
            width="100%",
            align="start",
            spacing="2",
        ),
        padding="1em",
    )


def production_rate_chart() -> rx.Component:
    """Line chart showing rate vs time with intervention line, base forecast, and Water Cut.
    
    Chart includes:
    - Actual production data (solid lines)
    - Intervention forecast (dashed lines) - versions 1,2,3
    - Base forecast (dotted lines) - version 0 (without intervention)
    - Water Cut on secondary Y-axis
    - Intervention date vertical reference line
    """
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.heading("Production Rate vs Time", size="4"),
                rx.spacer(),
                # Phase selection checkboxes
                rx.hstack(
                    rx.text("Show:", size="2", weight="bold"),
                    rx.checkbox(
                        "Oil",
                        checked=GTMState.show_oil,
                        on_change=GTMState.toggle_oil,
                        color_scheme="green",
                    ),
                    rx.checkbox(
                        "Liquid",
                        checked=GTMState.show_liquid,
                        on_change=GTMState.toggle_liquid,
                        color_scheme="blue",
                    ),
                    rx.checkbox(
                        "Water Cut",
                        checked=GTMState.show_wc,
                        on_change=GTMState.toggle_wc,
                        color_scheme="red",
                    ),
                    rx.checkbox(
                        "Base Forecast",
                        checked=GTMState.show_base_forecast,
                        on_change=GTMState.toggle_base_forecast,
                        color_scheme="gray",
                    ),
                    spacing="3",
                    align="center",
                ),
                width="100%",
                align="center",
            ),
            # Chart with dual Y-axes
            rx.recharts.composed_chart(
                # === ACTUAL DATA (solid lines) ===
                # Actual oil rate (left Y-axis)
                rx.cond(
                    GTMState.show_oil,
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
                ),
                # Actual liquid rate (left Y-axis)
                rx.cond(
                    GTMState.show_liquid,
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
                ),
                
                # === INTERVENTION FORECAST (dashed lines) ===
                # Forecast oil rate (left Y-axis)
                rx.cond(
                    GTMState.show_oil,
                    rx.recharts.line(
                        data_key="oilRateForecast",
                        name="Oil Rate (Intervention)",
                        stroke=rx.color("green", 10),
                        stroke_dasharray="5 5",
                        dot=False,
                        type_="monotone",
                        connect_nulls=True,
                        stroke_width=2,
                        y_axis_id="left",
                    ),
                    rx.fragment(),
                ),
                # Forecast liquid rate (left Y-axis)
                rx.cond(
                    GTMState.show_liquid,
                    rx.recharts.line(
                        data_key="liqRateForecast",
                        name="Liq Rate (Intervention)",
                        stroke=rx.color("blue", 10),
                        stroke_dasharray="5 5",
                        dot=False,
                        type_="monotone",
                        connect_nulls=True,
                        stroke_width=2,
                        y_axis_id="left",
                    ),
                    rx.fragment(),
                ),
                
                # === BASE FORECAST (dotted lines - without intervention) ===
                # Base oil rate (left Y-axis)
                rx.cond(
                    GTMState.show_oil & GTMState.show_base_forecast,
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
                ),
                # Base liquid rate (left Y-axis)
                rx.cond(
                    GTMState.show_liquid & GTMState.show_base_forecast,
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
                ),
                
                # === WATER CUT (right Y-axis) ===
                # Water Cut actual (right Y-axis)
                rx.cond(
                    GTMState.show_wc,
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
                ),
                # Water Cut forecast (right Y-axis)
                rx.cond(
                    GTMState.show_wc,
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
                ),
                # Water Cut base (right Y-axis)
                rx.cond(
                    GTMState.show_wc & GTMState.show_base_forecast,
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
                ),
                
                # Intervention vertical line
                rx.recharts.reference_line(
                    x=GTMState.intervention_date,
                    stroke=rx.color("orange", 9),
                    stroke_dasharray="3 3",
                    label="GTM",
                    stroke_width=2,
                ),
                rx.recharts.x_axis(
                    data_key="date",
                    angle=-45,
                    text_anchor="end",
                    height=80,
                    tick={"fontSize": 11}
                ),
                # Left Y-axis for Rate
                rx.recharts.y_axis(
                    y_axis_id="left",
                    orientation="left",
                    label={"value": "Rate (t/day)", "angle": -90, "position": "left", "offset": -0},
                    tick={"fontSize": 11},
                    stroke=rx.color("gray", 9),
                ),
                # Right Y-axis for Water Cut
                rx.recharts.y_axis(
                    y_axis_id="right",
                    orientation="right",
                    label={"value": "Water Cut (%)", "angle": 90, "position": "right", "offset": -10},
                    tick={"fontSize": 11},
                    domain=[0, 100],
                    stroke=rx.color("red", 9),
                ),
                rx.recharts.cartesian_grid(stroke_dasharray="3 3"),
                rx.recharts.graphing_tooltip(),
                rx.recharts.legend(icon_size=5),
                data=GTMState.chart_data,
                width="100%",
                height=400,
                margin={"bottom": 1, "left": 10, "right": 10, "top": 10},
            ),
            width="100%",
            align="center",
            spacing="3",
        ),
        padding="1em",
        width="100%"
    )