"""Well Intervention (GTM) management page - With Summary Tables and Batch Forecast."""
import reflex as rx
from ..templates.template import template
from ..states.gtm_state import GTMState
from ..components.charts import *
from ..components.tables import *
from ..components.dialogs import *


def intervention_table_section() -> rx.Component:
    """Left section: Intervention ID table with controls."""
    return rx.card(
        rx.vstack(
            # Header with buttons
            rx.hstack(
                rx.heading("Intervention ID", size="4"),
                rx.spacer(),
                rx.hstack(
                    search_interventions(),
                    add_intervention_button(),
                    load_intervention_button(),
                    spacing="2",
                ),
                width="100%",
                align="center",
            ),
            rx.divider(),
            # Table
            intervention_table(),
            width="100%",
            spacing="3",
        ),
        padding="1em",
        height="100%",
    )


def forecast_controls() -> rx.Component:
    """Forecast control panel with date input, version selector, and buttons."""
    return rx.hstack(
        rx.vstack(
            rx.text("Select Intervention:", size="1", weight="bold"),
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
            rx.icon("play", size=16),
            rx.text("Run Forecast", size="2"),
            on_click=GTMState.run_forecast,
            size="1",
        ),
        run_all_forecast_button(),
        spacing="3",
        align="end",
    )


def run_all_forecast_button() -> rx.Component:
    """Button to trigger batch forecast for all interventions with dialog."""
    return rx.dialog.root(
        rx.dialog.trigger(
            rx.button(
                rx.icon("play", size=16),
                rx.text("Run All Forecast", size="2"),
                color_scheme="red",
                size="1",
                disabled=GTMState.is_batch_forecasting,
            ),
        ),
        rx.dialog.content(
            rx.dialog.title(
                rx.hstack(
                    rx.icon("layers", size=20, color=rx.color("red", 9)),
                    rx.text("Batch Forecast - All Interventions"),
                    spacing="2",
                )
            ),
            rx.dialog.description(
                rx.text(
                    "Run DCA forecast for all interventions with ratio adjustment for Done wells.",
                    size="2"
                )
            ),
            rx.vstack(
                rx.callout(
                    rx.vstack(
                        rx.text("Ratio Adjustment Logic:", weight="bold", size="2"),
                        rx.text("• Plan wells: Standard hyperbolic Arps forecast", size="1"),
                        rx.text("• Done wells: ratio = actual_rate / forecast_rate", size="1"),
                        rx.text("• Forecast values adjusted by ratio factor", size="1"),
                        spacing="1",
                        align="start",
                    ),
                    icon="info",
                    color_scheme="blue",
                    size="1",
                ),
                rx.grid(
                    rx.card(
                        rx.vstack(
                            rx.hstack(
                                rx.icon("layers", size=18, color=rx.color("blue", 9)),
                                rx.text("Total Interventions", size="1", weight="bold"),
                                spacing="2",
                            ),
                            rx.heading(GTMState.total_interventions, size="5"),
                            spacing="1",
                            align="start",
                        ),
                        padding="1em",
                    ),
                    rx.card(
                        rx.vstack(
                            rx.hstack(
                                rx.icon("calendar", size=18, color=rx.color("orange", 9)),
                                rx.text("Forecast End Date", size="1", weight="bold"),
                                spacing="2",
                            ),
                            rx.cond(
                                GTMState.forecast_end_date != "",
                                rx.text(GTMState.forecast_end_date, weight="bold", size="2"),
                                rx.badge("Not Set", color_scheme="red", size="1"),
                            ),
                            spacing="1",
                            align="start",
                        ),
                        padding="1em",
                    ),
                    columns="2",
                    spacing="3",
                    width="100%",
                ),
                rx.cond(
                    GTMState.is_batch_forecasting,
                    batch_progress_panel(),
                    rx.fragment(),
                ),
                rx.cond(
                    (GTMState.batch_success_count > 0) | (GTMState.batch_error_count > 0),
                    batch_results_panel(),
                    rx.fragment(),
                ),
                rx.flex(
                    rx.dialog.close(
                        rx.button("Close", variant="soft", color_scheme="gray"),
                    ),
                    rx.cond(
                        GTMState.is_batch_forecasting,
                        rx.button(
                            rx.icon("x", size=14),
                            rx.text("Cancel", size="2"),
                            on_click=GTMState.cancel_batch_forecast,
                            color_scheme="red",
                            variant="soft",
                        ),
                        rx.button(
                            rx.icon("play", size=14),
                            rx.text("Start Batch Forecast", size="2"),
                            on_click=GTMState.run_forecast_all,
                            color_scheme="red",
                            disabled=GTMState.forecast_end_date == "",
                        ),
                    ),
                    spacing="3",
                    justify="end",
                    width="100%",
                ),
                spacing="4",
                width="100%",
            ),
            max_width="600px",
        ),
    )


def batch_progress_panel() -> rx.Component:
    """Progress panel shown during batch forecast execution."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.spinner(size="2"),
                rx.text("Batch Forecast in Progress...", weight="bold", size="2"),
                spacing="2",
            ),
            rx.progress(value=GTMState.batch_progress_percent, width="100%"),
            rx.hstack(
                rx.text(GTMState.batch_progress_display, size="1"),
                rx.text("|", size="1", color=rx.color("gray", 8)),
                rx.text(GTMState.batch_forecast_current, size="1", color=rx.color("gray", 10)),
                spacing="2",
            ),
            rx.hstack(
                rx.badge(
                    rx.hstack(
                        rx.icon("check", size=12),
                        rx.text(GTMState.batch_success_count, size="1"),
                        spacing="1",
                    ),
                    color_scheme="green",
                    size="1",
                ),
                rx.badge(
                    rx.hstack(
                        rx.icon("x", size=12),
                        rx.text(GTMState.batch_error_count, size="1"),
                        spacing="1",
                    ),
                    color_scheme="red",
                    size="1",
                ),
                spacing="2",
            ),
            spacing="2",
            width="100%",
        ),
        padding="1em",
        variant="surface",
    )


def batch_results_panel() -> rx.Component:
    """Results panel shown after batch forecast completion."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.icon("bar-chart-2", size=16, color=rx.color("green", 9)),
                rx.text("Batch Forecast Results", weight="bold", size="2"),
                spacing="2",
            ),
            rx.grid(
                rx.vstack(
                    rx.text("Success", size="1", color=rx.color("gray", 10)),
                    rx.heading(GTMState.batch_success_count, size="4", color=rx.color("green", 9)),
                    spacing="0",
                    align="center",
                ),
                rx.vstack(
                    rx.text("Errors", size="1", color=rx.color("gray", 10)),
                    rx.heading(GTMState.batch_error_count, size="4", color=rx.color("red", 9)),
                    spacing="0",
                    align="center",
                ),
                rx.vstack(
                    rx.text("Total Qoil (th.t)", size="1", color=rx.color("gray", 10)),
                    rx.heading(GTMState.batch_total_qoil_display, size="4", color=rx.color("blue", 9)),
                    spacing="0",
                    align="center",
                ),
                rx.vstack(
                    rx.text("Total Qliq (th.t)", size="1", color=rx.color("gray", 10)),
                    rx.heading(GTMState.batch_total_qliq_display, size="4", color=rx.color("blue", 9)),
                    spacing="0",
                    align="center",
                ),
                columns="4",
                spacing="3",
                width="100%",
            ),
            rx.cond(
                GTMState.batch_error_count > 0,
                rx.accordion.root(
                    rx.accordion.item(
                        header=rx.hstack(
                            rx.icon("alert-triangle", size=14, color=rx.color("yellow", 9)),
                            rx.text("View Errors", size="1"),
                            spacing="2",
                        ),
                        content=rx.box(
                            rx.foreach(
                                GTMState.batch_errors_display,
                                lambda err: rx.text(err, size="1", color=rx.color("red", 10))
                            ),
                            max_height="150px",
                            overflow_y="auto",
                        ),
                        value="errors",
                    ),
                    collapsible=True,
                    type="single",
                    width="100%",
                ),
                rx.fragment(),
            ),
            spacing="3",
            width="100%",
        ),
        padding="1em",
        variant="surface",
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
                on_change=lambda v: GTMState.set_forecast_version,
                size="1",
                width="80px",
            ),
            spacing="1",
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
                rx.divider(orientation="vertical", size="2"),
                rx.vstack(
                    rx.text("Type:", size="1", weight="bold"),
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
                    rx.text("Date:", size="1", weight="bold",align="center"),
                    rx.text(GTMState.intervention_date, size="1"),
                    spacing="0",
                ),
                rx.divider(orientation="vertical", size="2"),
                rx.badge(
                rx.vstack(
                    rx.text("qi_o / b_o / Di_o:", size="1", weight="bold",align="center"),
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
                spacing="9",
                padding="0.5em",
                background=rx.color("gray", 2),
                border_radius="6px",
                width="100%",
            ),
            spacing="2",
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
                rx.heading("Production Forecast", size="4"),
                rx.spacer(),
                forecast_controls(),
                width="100%",
                align="center",
            ),
            rx.divider(),
            # Two tables side by side
            rx.grid(
                # Production Records (from HistoryProd - last 5 years, showing last 24)
                rx.vstack(
                    rx.hstack(
                        rx.badge("Production History Last 5 Years", color_scheme="green", size="2"),
                        spacing="2",
                        align="center",
                    ),
                    production_table(GTMState.production_table_data),
                    width="100%",
                    spacing="2",
                ),
                # Forecast Results
                rx.vstack(
                    rx.hstack(
                        forecast_version_selector(),
                        rx.cond(
                            GTMState.has_base_forecast,
                            rx.badge("Base v0", color_scheme="gray", size="2"),
                            rx.badge("No base",color_scheme="yellow",size="2"),
                        ),
                        rx.cond(
                            GTMState.current_forecast_version > 0,
                            rx.button(
                                rx.icon("trash-2", size=14),
                                rx.text("Delete Version", size="1"),
                                color_scheme="red",
                                size="1",
                                on_click=lambda: GTMState.delete_current_forecast_version,
                            ),
                            rx.fragment(),
                        ),
                        spacing="2",
                        align="center",
                    ),
                    production_table(GTMState.forecast_table_data),
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


def summary_section() -> rx.Component:
    """Summary tables section showing Qoil forecast by month for current and next year."""
    return rx.vstack(
        rx.hstack(
            rx.hstack(
                rx.icon("table-2", size=20, color=rx.color("blue", 9)),
                rx.heading("Intervention Qoil Forecast Summary", size="5"),
                spacing="2",
                align="center",
            ),
            rx.spacer(),
            rx.button(
                rx.icon("file-spreadsheet", size=16),
                rx.text("Download All", size="2"),
                on_click=GTMState.download_both_years_excel,
                size="2",
                variant="soft",
                color_scheme="blue",
            ),
            width="100%",
            align="center",
        ),
        rx.divider(),
        rx.grid(
            current_year_intervention_table(),
            next_year_intervention_table(),
            columns="1",
            spacing="4",
            width="100%",
        ),
        width="100%",
        spacing="4",
    )


@template(
    route="/well-intervention",
    title="Well Intervention | Production Dashboard",
    description="Manage well intervention activities",
    on_load=GTMState.load_interventions,
)
def well_intervention_page() -> rx.Component:
    """Well Intervention management page with Summary Tables and Batch Forecast.
    
    Layout:
    - Top: Two-column grid (Left: Intervention Table | Right: Forecast/Production)
    - Middle: Rate vs Time scatter plot with intervention line
    - Bottom: Summary tables showing Qoil forecast by month for current and next year
    
    Features:
    - Production data from HistoryProd table (last 5 years)
    - Water Cut (WC) calculated as: WC = (Liqrate - Oilrate) / Liqrate * 100
    - Forecast versioning: Saves up to 3 forecast versions per intervention (FIFO)
    - Base forecast (v0): Production decline WITHOUT intervention for comparison
    - Version selector: Switch between different forecast versions
    - Auto-save: Forecasts automatically saved to InterventionForecast table
    - Summary Tables: Qoil by month for current year and next year
    - Excel Export: Download summary data as Excel files
    
    Batch Forecast (Run All):
    - For Plan wells: Standard hyperbolic Arps forecast from PlanningDate
    - For Done wells: Ratio adjustment = actual_rate / forecast_rate at last history
    - All subsequent forecast values multiplied by ratio
    
    DCA Formula: q(t) = qi / (1 + b * di * t)^(1/b) for hyperbolic
    
    Summary Table Columns:
    - UniqueId, Field, Platform, Reservoir, Type, Category, Status, Date, GTMYear
    - Jan, Feb, Mar, Apr, May, Jun, Jul, Aug, Sep, Oct, Nov, Dec, Total
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
            columns="2",
            spacing="4",
            width="100%",
        ),
        
        # Production Rate Chart
        rx.grid(
            production_rate_chart(state=GTMState),
            columns="2",
            spacing="4",
            width="100%"
        ),

        # Summary Tables Section
        summary_section(),
        
        align="start",
        spacing="4",
        width="100%",
    )