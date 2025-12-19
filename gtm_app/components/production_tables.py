"""Table and control components for Production page."""
import reflex as rx
from ..states.production_state import ProductionState


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
        # Run All Button
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
                # Requirements check
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
                
                # Stats
                rx.grid(
                    rx.card(
                        rx.vstack(
                            rx.text("Total Completions", size="1", color=rx.color("gray", 10)),
                            rx.heading(ProductionState.total_completions, size="4"),
                            spacing="0",
                            align="center",
                        ),
                        padding="1em",
                    ),
                    rx.card(
                        rx.vstack(
                            rx.text("Forecast End Date", size="1", color=rx.color("gray", 10)),
                            rx.cond(
                                ProductionState.forecast_end_date != "",
                                rx.text(ProductionState.forecast_end_date, weight="bold", size="2"),
                                rx.badge("Not Set", color_scheme="red", size="1"),
                            ),
                            spacing="0",
                            align="center",
                        ),
                        padding="1em",
                    ),
                    columns="2",
                    spacing="3",
                    width="100%",
                ),
                
                # Progress section (shown when running)
                rx.cond(
                    ProductionState.is_batch_forecasting,
                    batch_progress_panel(),
                    rx.fragment(),
                ),
                
                # Results section (shown after completion)
                rx.cond(
                    (ProductionState.batch_success_count > 0) | (ProductionState.batch_error_count > 0),
                    batch_results_panel(),
                    rx.fragment(),
                ),
                
                # Action buttons
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
                rx.icon("loader", size=16, color=rx.color("blue", 9)),
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
                    rx.heading(
                        ProductionState.batch_total_qoil_display,
                        size="4",
                        color=rx.color("blue", 9)
                    ),
                    spacing="0",
                    align="center",
                ),
                rx.vstack(
                    rx.text("Total Qliq (t)", size="1", color=rx.color("gray", 10)),
                    rx.heading(
                        ProductionState.batch_total_qliq_display,
                        size="4",
                        color=rx.color("blue", 9)
                    ),
                    spacing="0",
                    align="center",
                ),
                columns="4",
                spacing="3",
                width="100%",
            ),
            # Show errors if any
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
                                _render_error_text,
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


def _render_error_text(err: str) -> rx.Component:
    """Render error text item."""
    return rx.text(err, size="1", color=rx.color("red", 10))


def production_history_table() -> rx.Component:
    """Table showing production history from HistoryProd (last 24 records)."""
    return rx.box(
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell(rx.text("Date", size="1", weight="bold")),
                    rx.table.column_header_cell(rx.text("Oil Rate", size="1", weight="bold")),
                    rx.table.column_header_cell(rx.text("Liq Rate", size="1", weight="bold")),
                    rx.table.column_header_cell(rx.text("WC %", size="1", weight="bold")),
                ),
            ),
            rx.table.body(
                rx.foreach(
                    ProductionState.production_table_data,
                    _render_history_row,
                ),
            ),
            variant="surface",
            size="1",
            width="100%",
        ),
        overflow_y="auto",
        max_height="250px",
        width="100%",
    )


def _render_history_row(row: dict) -> rx.Component:
    """Render a single history table row."""
    return rx.table.row(
        rx.table.cell(rx.text(row["Date"], size="1")),
        rx.table.cell(rx.text(row["OilRate"], size="1")),
        rx.table.cell(rx.text(row["LiqRate"], size="1")),
        rx.table.cell(
            rx.badge(
                row["WC"],
                color_scheme=rx.cond(
                    row["WC_val"].to(float) > 80,
                    "red",
                    rx.cond(row["WC_val"].to(float) > 50, "yellow", "green")
                ),
                size="1"
            )
        ),
        style={"_hover": {"bg": rx.color("gray", 3)}},
    )


def forecast_result_table() -> rx.Component:
    """Table showing forecast results with cumulative production."""
    return rx.box(
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell(rx.text("Date", size="1", weight="bold")),
                    rx.table.column_header_cell(rx.text("Oil Rate", size="1", weight="bold")),
                    rx.table.column_header_cell(rx.text("Liq Rate", size="1", weight="bold")),
                    rx.table.column_header_cell(rx.text("Qoil (t)", size="1", weight="bold")),
                    rx.table.column_header_cell(rx.text("Qliq (t)", size="1", weight="bold")),
                    rx.table.column_header_cell(rx.text("WC %", size="1", weight="bold")),
                ),
            ),
            rx.table.body(
                rx.foreach(
                    ProductionState.forecast_table_data,
                    _render_forecast_row,
                ),
            ),
            variant="surface",
            size="1",
            width="100%",
        ),
        overflow_y="auto",
        max_height="250px",
        width="100%",
    )


def _render_forecast_row(row: dict) -> rx.Component:
    """Render a single forecast table row."""
    return rx.table.row(
        rx.table.cell(rx.text(row["Date"], size="1")),
        rx.table.cell(rx.text(row["OilRate"], size="1")),
        rx.table.cell(rx.text(row["LiqRate"], size="1")),
        rx.table.cell(rx.badge(row["Qoil"], color_scheme="green", size="1")),
        rx.table.cell(rx.badge(row["Qliq"], color_scheme="blue", size="1")),
        rx.table.cell(
            rx.badge(
                row["WC"],
                color_scheme=rx.cond(
                    row["WC_val"].to(float) > 80,
                    "red",
                    rx.cond(row["WC_val"].to(float) > 50, "yellow", "green")
                ),
                size="1"
            )
        ),
        style={"_hover": {"bg": rx.color("blue", 2)}},
    )


def production_rate_chart() -> rx.Component:
    """Line chart showing production rate vs time with DCA forecast and Water Cut."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.heading("Production Rate vs Time (Exponential DCA)", size="4"),
                rx.spacer(),
                rx.hstack(
                    rx.text("Show:", size="2", weight="bold"),
                    rx.checkbox("Oil", checked=ProductionState.show_oil, on_change=ProductionState.toggle_oil, color_scheme="green"),
                    rx.checkbox("Liquid", checked=ProductionState.show_liquid, on_change=ProductionState.toggle_liquid, color_scheme="blue"),
                    rx.checkbox("Water Cut", checked=ProductionState.show_wc, on_change=ProductionState.toggle_wc, color_scheme="red"),
                    spacing="3",
                    align="center",
                ),
                width="100%",
                align="center",
            ),
            rx.recharts.composed_chart(
                rx.cond(ProductionState.show_oil, rx.recharts.line(data_key="oilRate", name="Oil Rate (Actual)", stroke=rx.color("green", 9), dot=True, type_="monotone", connect_nulls=True, stroke_width=2, y_axis_id="left"), rx.fragment()),
                rx.cond(ProductionState.show_liquid, rx.recharts.line(data_key="liqRate", name="Liq Rate (Actual)", stroke=rx.color("blue", 9), dot=True, type_="monotone", connect_nulls=True, stroke_width=2, y_axis_id="left"), rx.fragment()),
                rx.cond(ProductionState.show_oil, rx.recharts.line(data_key="oilRateForecast", name="Oil Rate (Forecast)", stroke=rx.color("green", 10), stroke_dasharray="5 5", dot=False, type_="monotone", connect_nulls=True, stroke_width=2, y_axis_id="left"), rx.fragment()),
                rx.cond(ProductionState.show_liquid, rx.recharts.line(data_key="liqRateForecast", name="Liq Rate (Forecast)", stroke=rx.color("blue", 10), stroke_dasharray="5 5", dot=False, type_="monotone", connect_nulls=True, stroke_width=2, y_axis_id="left"), rx.fragment()),
                rx.cond(ProductionState.show_wc, rx.recharts.line(data_key="wc", name="Water Cut (%)", stroke=rx.color("red", 9), dot=True, type_="monotone", connect_nulls=True, stroke_width=2, y_axis_id="right"), rx.fragment()),
                rx.cond(ProductionState.show_wc, rx.recharts.line(data_key="wcForecast", name="Water Cut Forecast (%)", stroke=rx.color("red", 10), stroke_dasharray="5 5", dot=False, type_="monotone", connect_nulls=True, stroke_width=2, y_axis_id="right"), rx.fragment()),
                rx.recharts.x_axis(data_key="date", angle=-45, text_anchor="end", height=80, tick={"fontSize": 11}),
                rx.recharts.y_axis(y_axis_id="left", orientation="left", label={"value": "Rate (t/day)", "angle": -90, "position": "insideLeft", "offset": 10}, tick={"fontSize": 11}, stroke=rx.color("gray", 9)),
                rx.recharts.y_axis(y_axis_id="right", orientation="right", label={"value": "Water Cut (%)", "angle": 90, "position": "insideRight", "offset": 10}, tick={"fontSize": 11}, domain=[0, 100], stroke=rx.color("red", 9)),
                rx.recharts.cartesian_grid(stroke_dasharray="3 3"),
                rx.recharts.graphing_tooltip(),
                rx.recharts.legend(),
                data=ProductionState.chart_data,
                width="100%",
                height=350,
                margin={"bottom": 10, "left": 20, "right": 60, "top": 10},
            ),
            width="100%",
            align="center",
            spacing="3",
        ),
        padding="1em",
        width="100%",
    )