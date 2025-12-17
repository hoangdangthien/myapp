"""Well Intervention (GTM) management page - Reconstructed UI."""
import reflex as rx
from ..templates.template import template
from ..states.gtm_state import GTMState
from ..components.gtm_dialogs import add_gtm_button, load_excel_button, search_gtm
from ..components.gtm_table import (
    gtm_table, 
    production_record_table, 
    forecast_result_table,
    history_stats_card
)
from ..components.gtm_charts import production_rate_chart


def intervention_table_section() -> rx.Component:
    """Left section: Intervention ID table with controls."""
    return rx.card(
        rx.vstack(
            # Header with buttons
            rx.hstack(
                rx.heading("Intervention ID", size="4"),
                rx.spacer(),
                rx.hstack(
                    search_gtm(),
                    add_gtm_button(),
                    load_excel_button(),
                    spacing="2",
                ),
                width="100%",
                align="center",
            ),
            rx.divider(),
            # Table
            gtm_table(),
            width="100%",
            spacing="3",
        ),
        padding="1em",
        height="100%",
    )


def forecast_controls() -> rx.Component:
    """Forecast control panel with date input, version selector, and button."""
    return rx.hstack(
        rx.vstack(
            rx.text("Intervention ID:", size="1", weight="bold"),
            rx.select(
                GTMState.available_ids,
                value=GTMState.selected_id,
                on_change=GTMState.set_selected_id,
                size="1",
                width="150px",
            ),
            spacing="1",
        ),
        rx.vstack(
            rx.text("Forecast End Date", size="1", weight="bold"),
            rx.input(
                type="date",
                on_change=GTMState.set_forecast_end_date,
                width="150px",
                size="1",
            ),
            spacing="1",
        ),
        rx.button(
            rx.icon("trending-up", size=16),
            rx.text("Run Forecast", size="2"),
            on_click=GTMState.run_forecast,
            size="1",
        ),
        spacing="3",
        align="end",
    )


def forecast_version_selector() -> rx.Component:
    """Selector for viewing different forecast versions."""
    return rx.cond(
        GTMState.available_forecast_versions.length() > 0,
        rx.hstack(
            rx.text("Forecast Version:", size="1", weight="bold"),
            rx.select(
                GTMState.forecast_version_options,
                value=f"v{GTMState.current_forecast_version}",
                on_change=lambda v: GTMState.set_forecast_version_from_str,
                size="1",
                width="80px",
            ),
            #rx.badge(
                #f"{GTMState.available_forecast_versions.length()}/3 versions",
                #color_scheme="gray",
                #size="1",
            #),
            spacing="2",
            align="center",
        ),
        rx.text("No forecast versions available", size="1", color=rx.color("gray", 9)),
    )


def current_intervention_info() -> rx.Component:
    """Display current selected intervention info."""
    return rx.cond(
        GTMState.current_gtm,
        rx.vstack(
            rx.hstack(
                rx.vstack(
                    rx.text("Selected:", size="1", color=rx.color("gray", 10)),
                    rx.text(GTMState.selected_id, weight="bold", size="1"),
                    spacing="0",
                ),
                rx.divider(orientation="vertical", size="2"),
                rx.vstack(
                    rx.text("Type:", size="1", color=rx.color("gray", 10)),
                    rx.badge(
                        rx.cond(
                            GTMState.current_gtm,
                            GTMState.current_gtm.TypeGTM,
                            "-"
                        ),
                        color_scheme="blue",
                        size="1"
                    ),
                    spacing="0",
                ),
                rx.divider(orientation="vertical", size="2"),
                rx.vstack(
                    rx.text("Date:", size="1", color=rx.color("gray", 9)),
                    rx.text(GTMState.intervention_date, size="1"),
                    spacing="0",
                ),
                rx.divider(orientation="vertical", size="2"),
                rx.badge(
                rx.vstack(
                    rx.text("qi_o / b_o / Di_o:", size="1", color=rx.color("gray", 9)),
                    rx.text(
                        rx.cond(
                            GTMState.current_gtm,
                            f"{GTMState.current_gtm.InitialORate:.0f} / {GTMState.current_gtm.bo:.2f} / {GTMState.current_gtm.Dio:.3f}",
                            "-"
                        ),
                        size="1"
                    ),
                    spacing="0",
                ),
                color_scheme="green",
                ),
                rx.divider(orientation="vertical", size="2"),
                forecast_version_selector(),
                rx.divider(orientation="vertical", size="2"),
                rx.cond(
                    GTMState.current_forecast_version > 0,
                    rx.button(
                        rx.icon("trash-2", size=12),
                        rx.text("Delete Version", size="1"),
                        variant="ghost",
                        color_scheme="red",
                        size="1",
                        on_click=lambda: GTMState.delete_current_forecast_version,
                    ),
                    rx.fragment(),
                ),
                spacing="4",
                padding="0.5em",
                background=rx.color("gray", 2),
                border_radius="6px",
                width="100%",
            ),
            # History data stats (from HistoryProd - last 5 years)
            spacing="2",
            width="100%",
            #align="end",
        ),
        rx.text("Select an intervention", color=rx.color("gray", 10), size="2"),
    )


def forecast_section() -> rx.Component:
    """Right section: Forecast table and controls."""
    return rx.card(
        rx.vstack(
            # Header with forecast controls
            rx.hstack(
                rx.heading("Forecast & Production", size="4"),
                rx.spacer(),
                forecast_controls(),
                width="100%",
                align="center",
            ),
            rx.divider(),
            
            # Current intervention info with version selector
            current_intervention_info(),
            
            # Two tables side by side
            rx.grid(
                # Production Records (from HistoryProd - last 5 years, showing last 24)
                rx.vstack(
                    rx.hstack(
                        #rx.text("Production History", size="2", weight="bold"),
                        rx.badge("Production History Last 5 Years", color_scheme="green", size="2"),
                        spacing="2",
                        align="center",
                    ),
                    production_record_table(),
                    width="100%",
                    spacing="2",
                ),
                # Forecast Results
                rx.vstack(
                    rx.hstack(
                        #rx.text("Forecast Results", size="2", weight="bold"),
                        rx.cond(
                            GTMState.current_forecast_version > 0,
                            rx.badge(f"Forecast Results v{GTMState.current_forecast_version}", color_scheme="green", size="2"),
                            rx.fragment(),
                        ),
                        spacing="2",
                    ),
                    forecast_result_table(),
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
    route="/well-intervention",
    title="Well Intervention | GTM Dashboard",
    description="Manage well intervention activities",
    on_load=GTMState.load_gtms,
)
def well_intervention_page() -> rx.Component:
    """Well Intervention management page - Reconstructed UI.
    
    Layout:
    - Top: Two-column grid (Left: Intervention Table | Right: Forecast/Production)
    - Bottom: Rate vs Time scatter plot with intervention line
    
    Features:
    - Production data from HistoryProd table (last 5 years)
    - Water Cut (WC) calculated as: WC = (Liqrate - Oilrate) / Liqrate * 100
    - Forecast versioning: Saves up to 3 forecast versions per intervention (FIFO)
    - Version selector: Switch between different forecast versions
    - Auto-save: Forecasts automatically saved to InterventionProd table
    """
    return rx.vstack(
        # Page Header
        rx.hstack(
            
            rx.heading("Well Intervention Management", size="6"),
                
            rx.spacer(),
            rx.hstack(
                rx.badge(f"Total: {GTMState.total_interventions}", color_scheme="blue"),
                rx.badge(f"Planned: {GTMState.planned_interventions}", color_scheme="yellow"),
                rx.badge(f"Completed: {GTMState.completed_interventions}", color_scheme="green"),
                spacing="2",
            ),
            width="100%",
            align="center",
        ),
        rx.divider(),
        
        # Main content: Two columns
        rx.grid(
            # Left: Intervention ID Table
            intervention_table_section(),
            # Right: Forecast Section
            forecast_section(),
            production_rate_chart(),
            columns="2",
            rows="2",
            spacing="4",
            width="100%",
        ),
        
        align="start",
        spacing="4",
        width="100%",
    )