"""Refactored Chart and visualization components for Intervention data.

Uses shared components for consistent styling.
"""
import reflex as rx
from ..states.gtm_state import GTMState
from .shared_tables import stats_info_card
from .shared_charts import (
    chart_toggle_controls,
    dual_axis_line_chart,
    production_chart_card,
    bar_chart_simple,
)


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


def gtm_type_chart() -> rx.Component:
    """Bar chart showing GTM type distribution."""
    return rx.card(
        rx.vstack(
            rx.heading("Intervention Types", size="4"),
            bar_chart_simple(fig=GTMState.gtm_type_plotly), # Pass the plotly var
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
    toggle_controls = chart_toggle_controls(
        show_oil=GTMState.show_oil,
        show_liquid=GTMState.show_liquid,
        show_wc=GTMState.show_wc,
        toggle_oil=GTMState.toggle_oil,
        toggle_liquid=GTMState.toggle_liquid,
        toggle_wc=GTMState.toggle_wc,
        show_base_forecast=GTMState.show_base_forecast,
        toggle_base_forecast=GTMState.toggle_base_forecast,
    )
    
    chart = dual_axis_line_chart(
        fig=GTMState.plotly_dual_axis_chart # Inherited from SharedForecastState
    )
    
    return production_chart_card(
        title="Production Rate vs Time",
        chart_component=chart,
        toggle_controls=toggle_controls,
        show_legend=False # Plotly has its own legend now
    )