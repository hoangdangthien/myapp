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
        spacing="3",
        align="end",
    )


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
                    lambda row: rx.table.row(
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
                    lambda row: rx.table.row(
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
            rx.hstack(
                rx.badge(rx.hstack(rx.box(width="12px", height="3px", bg=rx.color("green", 9)), rx.text("Oil (Actual)", size="1"), spacing="1"), variant="soft"),
                rx.badge(rx.hstack(rx.box(width="12px", height="3px", bg=rx.color("blue", 9)), rx.text("Liquid (Actual)", size="1"), spacing="1"), variant="soft"),
                rx.badge(rx.hstack(rx.box(width="12px", height="3px", bg=rx.color("red", 9)), rx.text("Water Cut (%)", size="1"), spacing="1"), variant="soft"),
                rx.badge(rx.hstack(rx.box(width="12px", height="3px", bg=rx.color("gray", 6), style={"border_top": "2px dashed"}), rx.text("Forecast", size="1"), spacing="1"), variant="soft"),
                spacing="2",
                justify="center",
            ),
            width="100%",
            align="center",
            spacing="3",
        ),
        padding="1em",
        width="100%",
    )