"""Chart and visualization components for GTM data."""
import reflex as rx
from ..states.gtm_state import GTMState


def stats_card(
    title: str, 
    value: rx.Var, 
    icon: str,
    color_scheme: str = "accent"
) -> rx.Component:
    """Create a statistics card component.
    
    Args:
        title: Card title
        value: Statistic value (can be reactive)
        icon: Lucide icon name
        color_scheme: Color scheme for the card
    """
    return rx.card(
        rx.hstack(
            rx.vstack(
                rx.text(title, size="2", color=rx.color("gray", 11)),
                rx.heading(value, size="6"),
                align="start",
                spacing="1",
            ),
            rx.spacer(),
            rx.box(
                rx.icon(icon, size=24, color=rx.color(color_scheme, 9)),
                padding="0.75em",
                background=rx.color(color_scheme, 3),
                border_radius="8px",
            ),
            width="100%",
        ),
        padding="1.5em",
    )


def stats_cards() -> rx.Component:
    """Create the statistics cards section."""
    return rx.grid(
        stats_card(
            "Total Interventions",
            GTMState.total_interventions,
            "layers",
            "blue"
        ),
        stats_card(
            "Planned",
            GTMState.planned_interventions,
            "calendar",
            "yellow"
        ),
        stats_card(
            "Completed",
            GTMState.completed_interventions,
            "check-circle",
            "green"
        ),
        columns="3",
        spacing="4",
        width="100%",
    )


def gtm_type_chart() -> rx.Component:
    """Bar chart showing GTM type distribution."""
    return rx.card(
        rx.vstack(
            rx.heading("Intervention Types Distribution", size="4"),
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
                height=300,
            ),
            width="100%",
            align="start",
            spacing="3",
        ),
        padding="1.5em",
    )


def field_distribution_chart() -> rx.Component:
    """Pie chart showing distribution by field (placeholder for future)."""
    return rx.card(
        rx.vstack(
            rx.heading("Distribution by Field", size="4"),
            rx.text(
                "Coming soon - Field distribution analysis",
                color=rx.color("gray", 11),
            ),
            width="100%",
            align="start",
            spacing="3",
            min_height="200px",
        ),
        padding="1.5em",
    )
