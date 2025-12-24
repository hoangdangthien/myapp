import reflex as rx
from .shared_tables import stats_info_card
from ..states.gtm_state import GTMState


def stats_card(
    title: str,
    value: rx.Var,
    icon: str,
    color_scheme: str = "accent"
) -> rx.Component:
    """Create a statistics card component."""
    return stats_info_card(title, value, icon, color_scheme)


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