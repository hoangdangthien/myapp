"""Refactored table and control components for Production page.

Uses shared components for consistent styling.
"""
import reflex as rx
from ..states.production_state import ProductionState
from .shared_tables import (
    create_history_table,
    create_forecast_table,
    scrollable_table_container,
    version_selector,
    stats_info_card,
    empty_state,
    loading_spinner,
)
from .shared_charts import (
    chart_toggle_controls,
    dual_axis_line_chart,
    production_chart_card,
)


def forecast_controls() -> rx.Component:
    """Forecast control panel with UniqueId selector, date input, and run button."""
    return rx.hstack(
        rx.vstack(
            rx.text("Unique ID:", size="1", weight="bold"),
            rx.select(
                ProductionState.available_unique_ids,
                value=ProductionState.selected_unique_id,
                on_change=ProductionState.set_selected_unique_id,
                size="1",
                width="150px",
            ),
            spacing="1",
        ),
        rx.vstack(
            rx.text("Forecast End Date:", size="1", weight="bold"),
            rx.input(
                type="date",
                on_change=ProductionState.set_forecast_end_date,
                width="150px",
                size="1",
            ),
            spacing="1",
        ),
        rx.button(
            rx.icon("trending-up", size=16),
            rx.text("Run DCA Forecast", size="2"),
            on_click=ProductionState.run_forecast,
            size="2",
        ),
        run_all_forecast_button(),
        spacing="3",
        align="end",
    )


def run_all_forecast_button() -> rx.Component:
    """Button to trigger batch forecast for all completions with dialog."""
    return rx.dialog.root(
        rx.dialog.trigger(
            rx.button(
                rx.icon("layers", size=16),
                rx.text("Run All", size="2"),
                variant="soft",
                color_scheme="blue",
                size="2",
                disabled=ProductionState.is_batch_forecasting,
            ),
        ),
        rx.dialog.content(
            rx.dialog.title(
                rx.hstack(
                    rx.icon("layers", size=20, color=rx.color("blue", 9)),
                    rx.text("Batch Forecast - All Completions"),
                    spacing="2",
                )
            ),
            rx.dialog.description(
                rx.text(
                    "Run DCA forecast for all completions in the database. "
                    "This operation uses vectorized calculations and runs in the background.",
                    size="2"
                )
            ),
            rx.vstack(
                rx.callout(
                    rx.vstack(
                        rx.text("Before running:", weight="bold", size="2"),
                        rx.text("• Set Forecast End Date in the controls above", size="1"),
                        rx.text("• Ensure CompletionID has valid Di parameters", size="1"),
                        rx.text("• Completions without history will be skipped", size="1"),
                        spacing="1",
                        align="start",
                    ),
                    icon="info",
                    color_scheme="blue",
                    size="1",
                ),
                rx.grid(
                    stats_info_card("Total Completions", ProductionState.total_completions, "layers", "blue"),
                    rx.card(
                        rx.vstack(
                            rx.hstack(
                                rx.icon("calendar", size=18, color=rx.color("orange", 9)),
                                rx.text("Forecast End Date", size="1", weight="bold"),
                                spacing="2",
                            ),
                            rx.cond(
                                ProductionState.forecast_end_date != "",
                                rx.text(ProductionState.forecast_end_date, weight="bold", size="2"),
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
                    ProductionState.is_batch_forecasting,
                    batch_progress_panel(),
                    rx.fragment(),
                ),
                rx.cond(
                    (ProductionState.batch_success_count > 0) | (ProductionState.batch_error_count > 0),
                    batch_results_panel(),
                    rx.fragment(),
                ),
                rx.flex(
                    rx.dialog.close(
                        rx.button("Close", variant="soft", color_scheme="gray"),
                    ),
                    rx.cond(
                        ProductionState.is_batch_forecasting,
                        rx.button(
                            rx.icon("x", size=14),
                            rx.text("Cancel", size="2"),
                            on_click=ProductionState.cancel_batch_forecast,
                            color_scheme="red",
                            variant="soft",
                        ),
                        rx.button(
                            rx.icon("play", size=14),
                            rx.text("Start Batch Forecast", size="2"),
                            on_click=ProductionState.run_forecast_all,
                            color_scheme="blue",
                            disabled=ProductionState.forecast_end_date == "",
                        ),
                    ),
                    spacing="3",
                    justify="end",
                    width="100%",
                ),
                spacing="4",
                width="100%",
            ),
            max_width="550px",
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
            rx.progress(value=ProductionState.batch_progress_percent, width="100%"),
            rx.hstack(
                rx.text(ProductionState.batch_progress_display, size="1"),
                rx.text("|", size="1", color=rx.color("gray", 8)),
                rx.text(ProductionState.batch_forecast_current, size="1", color=rx.color("gray", 10)),
                spacing="2",
            ),
            rx.hstack(
                rx.badge(
                    rx.hstack(
                        rx.icon("check", size=12),
                        rx.text(ProductionState.batch_success_count, size="1"),
                        spacing="1",
                    ),
                    color_scheme="green",
                    size="1",
                ),
                rx.badge(
                    rx.hstack(
                        rx.icon("x", size=12),
                        rx.text(ProductionState.batch_error_count, size="1"),
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
                    rx.heading(ProductionState.batch_success_count, size="4", color=rx.color("green", 9)),
                    spacing="0",
                    align="center",
                ),
                rx.vstack(
                    rx.text("Errors", size="1", color=rx.color("gray", 10)),
                    rx.heading(ProductionState.batch_error_count, size="4", color=rx.color("red", 9)),
                    spacing="0",
                    align="center",
                ),
                rx.vstack(
                    rx.text("Total Qoil (t)", size="1", color=rx.color("gray", 10)),
                    rx.heading(ProductionState.batch_total_qoil_display, size="4", color=rx.color("blue", 9)),
                    spacing="0",
                    align="center",
                ),
                rx.vstack(
                    rx.text("Total Qliq (t)", size="1", color=rx.color("gray", 10)),
                    rx.heading(ProductionState.batch_total_qliq_display, size="4", color=rx.color("blue", 9)),
                    spacing="0",
                    align="center",
                ),
                columns="4",
                spacing="3",
                width="100%",
            ),
            rx.cond(
                ProductionState.batch_error_count > 0,
                rx.accordion.root(
                    rx.accordion.item(
                        header=rx.hstack(
                            rx.icon("alert-triangle", size=14, color=rx.color("yellow", 9)),
                            rx.text("View Errors", size="1"),
                            spacing="2",
                        ),
                        content=rx.box(
                            rx.foreach(
                                ProductionState.batch_errors_display,
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


def production_history_table() -> rx.Component:
    """Table showing production history from HistoryProd (last 24 records)."""
    return scrollable_table_container(
        create_history_table(ProductionState.production_table_data),
        max_height="250px"
    )


def forecast_result_table() -> rx.Component:
    """Table showing forecast results with cumulative production."""
    return scrollable_table_container(
        create_forecast_table(
            ProductionState.forecast_table_data,
            show_cumulative=True,
            columns=["Date", "Oil Rate", "Liq Rate", "Qoil (t)", "Qliq (t)", "WC %"]
        ),
        max_height="250px"
    )


def production_rate_chart() -> rx.Component:
    """Line chart showing production rate vs time with DCA forecast and Water Cut."""
    toggle_controls = chart_toggle_controls(
        show_oil=ProductionState.show_oil,
        show_liquid=ProductionState.show_liquid,
        show_wc=ProductionState.show_wc,
        toggle_oil=ProductionState.toggle_oil,
        toggle_liquid=ProductionState.toggle_liquid,
        toggle_wc=ProductionState.toggle_wc,
    )
    
    chart = dual_axis_line_chart(
        fig=ProductionState.plotly_dual_axis_chart
    )
    
    return production_chart_card(
        title="Production Rate vs Time",
        chart_component=chart,
        toggle_controls=toggle_controls,
        show_legend=False  # Plotly handles its own legend
    )

