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
    """Line chart showing rate vs time with intervention line and phase checkboxes."""
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
                    spacing="3",
                    align="center",
                ),
                width="100%",
                align="center",
            ),
            # Chart showing all phases (conditionally rendered based on checkboxes)
            rx.recharts.composed_chart(
                # Actual oil rate - conditionally shown
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
                    ),
                    rx.fragment(),
                ),
                # Actual liquid rate - conditionally shown
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
                    ),
                    rx.fragment(),
                ),
                # Forecast oil rate - conditionally shown
                rx.cond(
                    GTMState.show_oil,
                    rx.recharts.line(
                        data_key="oilRateForecast",
                        name="Oil Rate (Forecast)",
                        stroke=rx.color("green", 10),
                        stroke_dasharray="5 5",
                        dot=False,
                        type_="monotone",
                        connect_nulls=True,
                        stroke_width=2,
                    ),
                    rx.fragment(),
                ),
                # Forecast liquid rate - conditionally shown
                rx.cond(
                    GTMState.show_liquid,
                    rx.recharts.line(
                        data_key="liqRateForecast",
                        name="Liq Rate (Forecast)",
                        stroke=rx.color("blue", 10),
                        stroke_dasharray="5 5",
                        dot=False,
                        type_="monotone",
                        connect_nulls=True,
                        stroke_width=2,
                    ),
                    rx.fragment(),
                ),
                # Intervention vertical line
                rx.recharts.reference_line(
                    x=GTMState.intervention_date,
                    stroke=rx.color("red", 9),
                    stroke_dasharray="3 3",
                    label="GTM",
                    stroke_width=2,
                ),
                rx.recharts.x_axis(data_key="date", angle=-45, text_anchor="end", height=80,tick={"fontSize":12}),
                rx.recharts.y_axis(label={"value": "Rate (t/day)", "angle": -90, "position": "Center", "offset":30},tick={"fontSize":12}),
                rx.recharts.cartesian_grid(stroke_dasharray="3 3"),
                rx.recharts.graphing_tooltip(),
                rx.recharts.legend(),
                data=GTMState.chart_data,
                width="100%",
                height=350,
                margin={"bottom": 10, "left": 20, "right": 20, "top": 10},
            ),
            # Legend
            rx.hstack(
                rx.badge(
                    rx.hstack(
                        rx.box(width="12px", height="3px", bg=rx.color("green", 9)),
                        rx.text("Oil Rate (Actual)", size="1"),
                        spacing="1",
                    ),
                    variant="soft",
                ),
                rx.badge(
                    rx.hstack(
                        rx.box(width="12px", height="3px", bg=rx.color("blue", 9)),
                        rx.text("Liquid Rate (Actual)", size="1"),
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
                rx.badge(
                    rx.hstack(
                        rx.box(width="12px", height="3px", bg=rx.color("red", 9)),
                        rx.text("Intervention Date", size="1"),
                        spacing="1",
                    ),
                    variant="soft",
                ),
                spacing="2",
                justify="center",
            ),
            width="100%",
            align="center",
            spacing="3",
        ),
        padding="1em",
        width="100%"
    )