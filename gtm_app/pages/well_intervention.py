"""Well Intervention (GTM) management page - Reconstructed UI."""
import reflex as rx
from ..templates.template import template
from ..states.gtm_state import GTMState
from ..components.gtm_dialogs import add_gtm_button, load_excel_button
from ..components.gtm_table import gtm_table, production_record_table, forecast_result_table
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
    """Forecast control panel with date input and button."""
    return rx.hstack(
        rx.vstack(
            rx.text("Forecast End Date", size="1", weight="bold"),
            rx.input(
                type="date",
                on_change=GTMState.set_forecast_end_date,
                width="150px",
                size="2",
            ),
            spacing="1",
        ),
        rx.button(
            rx.icon("trending-up", size=16),
            rx.text("Run Forecast", size="2"),
            on_click=GTMState.run_forecast,
            size="2",
        ),
        spacing="3",
        align="end",
    )


def current_intervention_info() -> rx.Component:
    """Display current selected intervention info."""
    return rx.cond(
        GTMState.current_gtm,
        rx.hstack(
            rx.vstack(
                rx.text("Selected:", size="1", color=rx.color("gray", 10)),
                rx.text(GTMState.selected_id, weight="bold", size="2"),
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
                rx.text("Date:", size="1", color=rx.color("gray", 10)),
                rx.text(GTMState.intervention_date, size="2"),
                spacing="0",
            ),
            rx.divider(orientation="vertical", size="2"),
            rx.vstack(
                rx.text("qi_o / b_o / Di_o:", size="1", color=rx.color("gray", 10)),
                rx.text(
                    rx.cond(
                        GTMState.current_gtm,
                        f"{GTMState.current_gtm.InitialORate:.0f} / {GTMState.current_gtm.bo:.2f} / {GTMState.current_gtm.Dio:.3f}",
                        "-"
                    ),
                    size="2"
                ),
                spacing="0",
            ),
            spacing="4",
            padding="0.5em",
            background=rx.color("gray", 2),
            border_radius="6px",
            width="100%",
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
            
            # Current intervention info
            current_intervention_info(),
            
            # Two tables side by side
            rx.grid(
                # Production Records
                rx.vstack(
                    rx.text("Production Records (Last 10)", size="2", weight="bold"),
                    production_record_table(),
                    width="100%",
                    spacing="2",
                ),
                # Forecast Results
                rx.vstack(
                    rx.text("Forecast Results", size="2", weight="bold"),
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
    """
    return rx.vstack(
        # Page Header
        rx.hstack(
            rx.vstack(
                rx.heading("Well Intervention Management", size="6"),
                rx.text(
                    "Manage interventions and forecast production using Arps decline curve",
                    color=rx.color("gray", 11),
                    size="2",
                ),
                align="start",
                spacing="1",
            ),
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
            columns="2",
            spacing="4",
            width="100%",
        ),
        
        # Bottom: Production Rate Chart
        production_rate_chart(),
        
        align="start",
        spacing="4",
        width="100%",
    )
