"""Components for Production monitoring page with DCA forecasting."""
import reflex as rx
from ..states.production_state import ProductionState
from ..models import CompletionID


def completion_filter_controls() -> rx.Component:
    """Filter controls for CompletionID table."""
    return rx.hstack(
        rx.input(
            rx.input.slot(rx.icon("search")),
            placeholder="Search by ID or Well name...",
            size="2",
            width="220px",
            on_change=ProductionState.filter_completions,
            debounce_timeout=300,  # 300ms debounce to prevent lag
        ),
        rx.select(
            ProductionState.unique_reservoirs,
            placeholder="Filter by Reservoir",
            size="2",
            width="180px",
            on_change=ProductionState.filter_by_reservoir,
        ),
        spacing="2",
        align="center",
    )


def show_completion_row(completion: CompletionID) -> rx.Component:
    """Display a completion in a table row."""
    return rx.table.row(
        rx.table.cell(
            rx.text(completion.UniqueId, size="1", weight="medium"),
        ),
        rx.table.cell(
            rx.text(
                rx.cond(completion.WellName, completion.WellName, "-"),
                size="1"
            )
        ),
        rx.table.cell(
            rx.badge(
                rx.cond(completion.Reservoir, completion.Reservoir, "-"),
                color_scheme="blue",
                size="1"
            ),
        ),
        rx.table.cell(
            rx.text(
                rx.cond(completion.Completion, completion.Completion, "-"),
                size="1"
            )
        ),
        rx.table.cell(
            rx.text(
                rx.cond(
                    completion.KH,
                    completion.KH.to(str),
                    "-"
                ),
                size="1"
            )
        ),
        rx.table.cell(
            rx.badge(
                rx.cond(
                    completion.Do,
                    completion.Do.to(str),
                    "-"
                ),
                color_scheme="orange",
                size="1"
            ),
        ),
        rx.table.cell(
            rx.badge(
                rx.cond(
                    completion.Dl,
                    completion.Dl.to(str),
                    "-"
                ),
                color_scheme="orange",
                size="1"
            ),
        ),
        style={"_hover": {"bg": rx.color("gray", 3)}, "cursor": "pointer"},
        align="center",
        on_click=lambda: ProductionState.set_selected_unique_id(completion.UniqueId),
    )


def completion_table() -> rx.Component:
    """Main CompletionID table component."""
    return rx.box(
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell(rx.text("Unique ID", size="1", weight="bold")),
                    rx.table.column_header_cell(rx.text("Well Name", size="1", weight="bold")),
                    rx.table.column_header_cell(rx.text("Reservoir", size="1", weight="bold")),
                    rx.table.column_header_cell(rx.text("Completion", size="1", weight="bold")),
                    rx.table.column_header_cell(rx.text("KH", size="1", weight="bold")),
                    rx.table.column_header_cell(rx.text("Doil", size="1", weight="bold")),
                    rx.table.column_header_cell(rx.text("Dliq", size="1", weight="bold")),
                ),
            ),
            rx.table.body(
                rx.foreach(
                    ProductionState.completions,
                    show_completion_row
                ),
            ),
            variant="surface",
            size="1",
            width="100%",
        ),
        overflow_x="auto",
        overflow_y="auto",
        max_height="300px",
        width="100%",
    )


def completion_stats_summary() -> rx.Component:
    """Summary statistics cards for completions."""
    return rx.grid(
        rx.card(
            rx.vstack(
                rx.hstack(
                    rx.icon("layers", size=18, color=rx.color("blue", 9)),
                    rx.text("Total Completions", size="1", weight="bold"),
                    spacing="2",
                ),
                rx.heading(ProductionState.total_completions, size="5"),
                spacing="1",
                align="start",
            ),
            padding="1em",
        ),
        rx.card(
            rx.vstack(
                rx.hstack(
                    rx.icon("database", size=18, color=rx.color("green", 9)),
                    rx.text("History Records", size="1", weight="bold"),
                    spacing="2",
                ),
                rx.heading(ProductionState.history_record_count, size="5"),
                spacing="1",
                align="start",
            ),
            padding="1em",
        ),
        rx.card(
            rx.vstack(
                rx.hstack(
                    rx.icon("calendar", size=18, color=rx.color("orange", 9)),
                    rx.text("Date Range (5Y)", size="1", weight="bold"),
                    spacing="2",
                ),
                rx.text(ProductionState.date_range_display, size="2"),
                spacing="1",
                align="start",
            ),
            padding="1em",
        ),
        columns="3",
        spacing="3",
        width="100%",
    )


def selected_completion_info() -> rx.Component:
    """Display selected completion info with DCA parameters."""
    return rx.cond(
        ProductionState.selected_unique_id != "",
        rx.card(
            rx.vstack(
                rx.hstack(
                    rx.vstack(
                        rx.text("Selected:", size="1", color=rx.color("gray", 10)),
                        rx.text(ProductionState.selected_unique_id, weight="bold", size="2"),
                        spacing="0",
                    ),
                    rx.divider(orientation="vertical", size="2"),
                    rx.vstack(
                        rx.text("Well:", size="1", color=rx.color("gray", 10)),
                        rx.text(ProductionState.selected_wellname, size="1"),
                        spacing="0",
                    ),
                    rx.divider(orientation="vertical", size="2"),
                    rx.vstack(
                        rx.text("Reservoir:", size="1", color=rx.color("gray", 10)),
                        rx.badge(
                            ProductionState.selected_reservoir_name,
                            color_scheme="blue",
                            size="1"
                        ),
                        spacing="0",
                    ),
                    rx.divider(orientation="vertical", size="2"),
                    rx.badge(
                        rx.vstack(
                            rx.text("DCA Params:", size="1", color=rx.color("gray", 10)),
                            rx.text(ProductionState.dca_parameters_display, size="1"),
                            spacing="0",
                        ),
                        color_scheme="green",
                    ),
                    rx.divider(orientation="vertical", size="2"),
                    forecast_version_selector(),
                    rx.cond(
                        ProductionState.current_forecast_version > 0,
                        rx.button(
                            rx.icon("trash-2", size=12),
                            rx.text("Delete", size="1"),
                            variant="ghost",
                            color_scheme="red",
                            size="1",
                            on_click=ProductionState.delete_current_forecast_version,
                        ),
                        rx.fragment(),
                    ),
                    spacing="3",
                    padding="0.5em",
                    background=rx.color("gray", 2),
                    border_radius="6px",
                    width="100%",
                    align="center",
                ),
                # Intervention warning if planned
                rx.cond(
                    ProductionState.has_planned_intervention,
                    rx.hstack(
                        rx.icon("alert-triangle", size=14, color=rx.color("yellow", 9)),
                        rx.text(
                            ProductionState.intervention_info,
                            size="1",
                            color=rx.color("yellow", 11)
                        ),
                        rx.badge("Will save to InterventionProd v0", color_scheme="yellow", size="1"),
                        spacing="2",
                        padding="0.5em",
                        background=rx.color("yellow", 3),
                        border_radius="4px",
                    ),
                    rx.fragment(),
                ),
                spacing="2",
                width="100%",
            ),
            padding="0.75em",
        ),
        rx.text("Select a completion from the table", color=rx.color("gray", 10), size="2"),
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
        spacing="3",
        align="end",
    )


def forecast_version_selector() -> rx.Component:
    """Selector for viewing different forecast versions."""
    return rx.cond(
        ProductionState.available_forecast_versions.length() > 0,
        rx.hstack(
            rx.text("Version:", size="1", weight="bold"),
            rx.select(
                ProductionState.forecast_version_options,
                value=ProductionState.current_version_display,
                on_change=ProductionState.set_forecast_version_from_str,
                size="1",
                width="70px",
            ),
            rx.badge(
                ProductionState.version_count_display,
                color_scheme="gray",
                size="1",
            ),
            spacing="2",
            align="center",
        ),
        rx.text("No forecasts", size="1", color=rx.color("gray", 9)),
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
                                    rx.cond(
                                        row["WC_val"].to(float) > 50,
                                        "yellow",
                                        "green"
                                    )
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
    """Table showing forecast results."""
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
                    ProductionState.forecast_table_data,
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
                                    rx.cond(
                                        row["WC_val"].to(float) > 50,
                                        "yellow",
                                        "green"
                                    )
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
    """Line chart showing production rate vs time with DCA forecast and Water Cut on secondary axis."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.heading("Production Rate vs Time (Exponential DCA)", size="4"),
                rx.spacer(),
                rx.hstack(
                    rx.text("Show:", size="2", weight="bold"),
                    rx.checkbox(
                        "Oil",
                        checked=ProductionState.show_oil,
                        on_change=ProductionState.toggle_oil,
                        color_scheme="green",
                    ),
                    rx.checkbox(
                        "Liquid",
                        checked=ProductionState.show_liquid,
                        on_change=ProductionState.toggle_liquid,
                        color_scheme="blue",
                    ),
                    rx.checkbox(
                        "Water Cut",
                        checked=ProductionState.show_wc,
                        on_change=ProductionState.toggle_wc,
                        color_scheme="red",
                    ),
                    spacing="3",
                    align="center",
                ),
                width="100%",
                align="center",
            ),
            rx.recharts.composed_chart(
                # Actual oil rate (left Y-axis)
                rx.cond(
                    ProductionState.show_oil,
                    rx.recharts.line(
                        data_key="oilRate",
                        name="Oil Rate (Actual)",
                        stroke=rx.color("green", 9),
                        dot=True,
                        type_="monotone",
                        connect_nulls=True,
                        stroke_width=2,
                        y_axis_id="left",
                    ),
                    rx.fragment(),
                ),
                # Actual liquid rate (left Y-axis)
                rx.cond(
                    ProductionState.show_liquid,
                    rx.recharts.line(
                        data_key="liqRate",
                        name="Liq Rate (Actual)",
                        stroke=rx.color("blue", 9),
                        dot=True,
                        type_="monotone",
                        connect_nulls=True,
                        stroke_width=2,
                        y_axis_id="left",
                    ),
                    rx.fragment(),
                ),
                # Forecast oil rate (left Y-axis)
                rx.cond(
                    ProductionState.show_oil,
                    rx.recharts.line(
                        data_key="oilRateForecast",
                        name="Oil Rate (Forecast)",
                        stroke=rx.color("green", 10),
                        stroke_dasharray="5 5",
                        dot=False,
                        type_="monotone",
                        connect_nulls=True,
                        stroke_width=2,
                        y_axis_id="left",
                    ),
                    rx.fragment(),
                ),
                # Forecast liquid rate (left Y-axis)
                rx.cond(
                    ProductionState.show_liquid,
                    rx.recharts.line(
                        data_key="liqRateForecast",
                        name="Liq Rate (Forecast)",
                        stroke=rx.color("blue", 10),
                        stroke_dasharray="5 5",
                        dot=False,
                        type_="monotone",
                        connect_nulls=True,
                        stroke_width=2,
                        y_axis_id="left",
                    ),
                    rx.fragment(),
                ),
                # Water Cut (right Y-axis)
                rx.cond(
                    ProductionState.show_wc,
                    rx.recharts.line(
                        data_key="wc",
                        name="Water Cut (%)",
                        stroke=rx.color("red", 9),
                        dot=True,
                        type_="monotone",
                        connect_nulls=True,
                        stroke_width=2,
                        y_axis_id="right",
                    ),
                    rx.fragment(),
                ),
                # Forecast Water Cut (right Y-axis)
                rx.cond(
                    ProductionState.show_wc,
                    rx.recharts.line(
                        data_key="wcForecast",
                        name="Water Cut Forecast (%)",
                        stroke=rx.color("red", 10),
                        stroke_dasharray="5 5",
                        dot=False,
                        type_="monotone",
                        connect_nulls=True,
                        stroke_width=2,
                        y_axis_id="right",
                    ),
                    rx.fragment(),
                ),
                rx.recharts.x_axis(
                    data_key="date",
                    angle=-45,
                    text_anchor="end",
                    height=80,
                    tick={"fontSize": 11}
                ),
                # Left Y-axis for Rate
                rx.recharts.y_axis(
                    y_axis_id="left",
                    orientation="left",
                    label={"value": "Rate (t/day)", "angle": -90, "position": "insideLeft", "offset": 10},
                    tick={"fontSize": 11},
                    stroke=rx.color("gray", 9),
                ),
                # Right Y-axis for Water Cut
                rx.recharts.y_axis(
                    y_axis_id="right",
                    orientation="right",
                    label={"value": "Water Cut (%)", "angle": 90, "position": "insideRight", "offset": 10},
                    tick={"fontSize": 11},
                    domain=[0, 100],
                    stroke=rx.color("red", 9),
                ),
                rx.recharts.cartesian_grid(stroke_dasharray="3 3"),
                rx.recharts.graphing_tooltip(),
                rx.recharts.legend(),
                data=ProductionState.chart_data,
                width="100%",
                height=350,
                margin={"bottom": 10, "left": 20, "right": 60, "top": 10},
            ),
            # Legend
            rx.hstack(
                rx.badge(
                    rx.hstack(
                        rx.box(width="12px", height="3px", bg=rx.color("green", 9)),
                        rx.text("Oil (Actual)", size="1"),
                        spacing="1",
                    ),
                    variant="soft",
                ),
                rx.badge(
                    rx.hstack(
                        rx.box(width="12px", height="3px", bg=rx.color("blue", 9)),
                        rx.text("Liquid (Actual)", size="1"),
                        spacing="1",
                    ),
                    variant="soft",
                ),
                rx.badge(
                    rx.hstack(
                        rx.box(width="12px", height="3px", bg=rx.color("red", 9)),
                        rx.text("Water Cut (%)", size="1"),
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