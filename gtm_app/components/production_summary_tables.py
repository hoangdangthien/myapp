"""Production Summary Table Components.

Summary tables showing Rate and Q (cumulative production) by month for two years.
Supports phase selection (oil/liquid) and Excel download.
"""
import reflex as rx
from ..states.production_state import ProductionState


def phase_selector() -> rx.Component:
    """Phase selector toggle for oil/liquid."""
    return rx.hstack(
        rx.text("Phase:", size="2", weight="bold"),
        rx.select(
            ["oil","liquid"],
            value=ProductionState.selected_phase,
            on_change=ProductionState.set_selected_phase,
            size="1",
        ),
        spacing="2",
        align="center",
    )


def summary_rate_row(row: dict) -> rx.Component:
    """Render a single row in the rate summary table."""
    return rx.table.row(
        rx.table.cell(rx.text(row["UniqueId"], size="1", weight="medium")),
        rx.table.cell(rx.text(row["Field"], size="1")),
        rx.table.cell(rx.text(row["Platform"], size="1")),
        rx.table.cell(rx.badge(row["Reservoir"], color_scheme="blue", size="1")),
        rx.table.cell(rx.text(row["Jan"], size="1")),
        rx.table.cell(rx.text(row["Feb"], size="1")),
        rx.table.cell(rx.text(row["Mar"], size="1")),
        rx.table.cell(rx.text(row["Apr"], size="1")),
        rx.table.cell(rx.text(row["May"], size="1")),
        rx.table.cell(rx.text(row["Jun"], size="1")),
        rx.table.cell(rx.text(row["Jul"], size="1")),
        rx.table.cell(rx.text(row["Aug"], size="1")),
        rx.table.cell(rx.text(row["Sep"], size="1")),
        rx.table.cell(rx.text(row["Oct"], size="1")),
        rx.table.cell(rx.text(row["Nov"], size="1")),
        rx.table.cell(rx.text(row["Dec"], size="1")),
        rx.table.cell(
            rx.badge(row["Avg"], color_scheme="green", size="1", variant="solid")
        ),
        style={"_hover": {"bg": rx.color("gray", 3)}},
        align="center",
    )


def summary_q_row(row: dict) -> rx.Component:
    """Render a single row in the Q (cumulative) summary table."""
    return rx.table.row(
        rx.table.cell(rx.text(row["UniqueId"], size="1", weight="medium")),
        rx.table.cell(rx.text(row["Field"], size="1")),
        rx.table.cell(rx.text(row["Platform"], size="1")),
        rx.table.cell(rx.badge(row["Reservoir"], color_scheme="blue", size="1")),
        rx.table.cell(rx.text(row["Jan"], size="1")),
        rx.table.cell(rx.text(row["Feb"], size="1")),
        rx.table.cell(rx.text(row["Mar"], size="1")),
        rx.table.cell(rx.text(row["Apr"], size="1")),
        rx.table.cell(rx.text(row["May"], size="1")),
        rx.table.cell(rx.text(row["Jun"], size="1")),
        rx.table.cell(rx.text(row["Jul"], size="1")),
        rx.table.cell(rx.text(row["Aug"], size="1")),
        rx.table.cell(rx.text(row["Sep"], size="1")),
        rx.table.cell(rx.text(row["Oct"], size="1")),
        rx.table.cell(rx.text(row["Nov"], size="1")),
        rx.table.cell(rx.text(row["Dec"], size="1")),
        rx.table.cell(
            rx.badge(row["Total"], color_scheme="green", size="1", variant="solid")
        ),
        style={"_hover": {"bg": rx.color("gray", 3)}},
        align="center",
    )


def summary_rate_header() -> rx.Component:
    """Header for rate summary tables."""
    return rx.table.header(
        rx.table.row(
            rx.table.column_header_cell(rx.text("UniqueId", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Field", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Platform", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Reservoir", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Jan", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Feb", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Mar", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Apr", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("May", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Jun", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Jul", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Aug", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Sep", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Oct", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Nov", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Dec", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Avg", size="1", weight="bold")),
        ),
    )


def summary_q_header() -> rx.Component:
    """Header for Q (cumulative) summary tables."""
    return rx.table.header(
        rx.table.row(
            rx.table.column_header_cell(rx.text("UniqueId", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Field", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Platform", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Reservoir", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Jan", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Feb", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Mar", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Apr", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("May", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Jun", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Jul", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Aug", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Sep", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Oct", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Nov", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Dec", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Total(th.t)", size="1", weight="bold")),
        ),
    )


def current_year_rate_table() -> rx.Component:
    """Rate summary table for current year."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.hstack(
                    rx.icon("activity", size=18, color=rx.color("blue", 9)),
                    rx.heading(
                        f"Rate Forecast {ProductionState.current_year} - {ProductionState.phase_display} (t/day)", 
                        size="4"
                    ),
                    spacing="2",
                    align="center",
                ),
                rx.spacer(),
                rx.hstack(
                    rx.badge(
                        rx.hstack(
                            rx.text("Completions:", size="1"),
                            rx.text(ProductionState.current_year_rate_count, weight="bold", size="1"),
                            spacing="1",
                        ),
                        color_scheme="blue",
                        size="1",
                    ),
                    rx.button(
                        rx.icon("download", size=14),
                        rx.text("Excel", size="1"),
                        on_click=ProductionState.download_current_year_rate_excel,
                        size="1",
                        variant="soft",
                        color_scheme="green",
                    ),
                    spacing="2",
                    align="center",
                ),
                width="100%",
                align="center",
            ),
            rx.divider(),
            rx.cond(
                ProductionState.current_year_rate_count > 0,
                rx.box(
                    rx.table.root(
                        summary_rate_header(),
                        rx.table.body(
                            rx.foreach(
                                ProductionState.current_year_rate_display_data,
                                summary_rate_row
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
                ),
                rx.center(
                    rx.vstack(
                        rx.icon("inbox", size=32, color=rx.color("gray", 8)),
                        rx.text(
                            "No rate forecast data for current year",
                            size="2",
                            color=rx.color("gray", 10)
                        ),
                        spacing="2",
                        align="center",
                    ),
                    padding="2em",
                ),
            ),
            width="100%",
            spacing="3",
        ),
        padding="1em",
        width="100%",
    )


def next_year_rate_table() -> rx.Component:
    """Rate summary table for next year."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.hstack(
                    rx.icon("activity", size=18, color=rx.color("orange", 9)),
                    rx.heading(
                        f"Rate Forecast {ProductionState.next_year} - {ProductionState.phase_display} (t/day)", 
                        size="4"
                    ),
                    spacing="2",
                    align="center",
                ),
                rx.spacer(),
                rx.hstack(
                    rx.badge(
                        rx.hstack(
                            rx.text("Completions:", size="1"),
                            rx.text(ProductionState.next_year_rate_count, weight="bold", size="1"),
                            spacing="1",
                        ),
                        color_scheme="orange",
                        size="1",
                    ),
                    rx.button(
                        rx.icon("download", size=14),
                        rx.text("Excel", size="1"),
                        on_click=ProductionState.download_next_year_rate_excel,
                        size="1",
                        variant="soft",
                        color_scheme="green",
                    ),
                    spacing="2",
                    align="center",
                ),
                width="100%",
                align="center",
            ),
            rx.divider(),
            rx.cond(
                ProductionState.next_year_rate_count > 0,
                rx.box(
                    rx.table.root(
                        summary_rate_header(),
                        rx.table.body(
                            rx.foreach(
                                ProductionState.next_year_rate_display_data,
                                summary_rate_row
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
                ),
                rx.center(
                    rx.vstack(
                        rx.icon("inbox", size=32, color=rx.color("gray", 8)),
                        rx.text(
                            "No rate forecast data for next year",
                            size="2",
                            color=rx.color("gray", 10)
                        ),
                        spacing="2",
                        align="center",
                    ),
                    padding="2em",
                ),
            ),
            width="100%",
            spacing="3",
        ),
        padding="1em",
        width="100%",
    )


def current_year_q_table() -> rx.Component:
    """Q (cumulative) summary table for current year."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.hstack(
                    rx.icon("bar-chart-2", size=18, color=rx.color("green", 9)),
                    rx.heading(
                        rx.cond(
                            ProductionState.is_oil_phase,
                            f"Qoil Forecast {ProductionState.current_year} (tons)",
                            f"Qliq Forecast {ProductionState.current_year} (tons)"
                        ),
                        size="4"
                    ),
                    spacing="2",
                    align="center",
                ),
                rx.spacer(),
                rx.hstack(
                    rx.badge(
                        rx.hstack(
                            rx.text("Completions:", size="1"),
                            rx.text(ProductionState.current_year_q_count, weight="bold", size="1"),
                            spacing="1",
                        ),
                        color_scheme="green",
                        size="1",
                    ),
                    rx.badge(
                        rx.hstack(
                            rx.text("Total:", size="1"),
                            rx.cond(
                                ProductionState.is_oil_phase,
                                rx.text(
                                    ProductionState.current_year_total_qoil.to(int).to(str),
                                    weight="bold",
                                    size="1"
                                ),
                                rx.text(
                                    ProductionState.current_year_total_qliq.to(int).to(str),
                                    weight="bold",
                                    size="1"
                                ),
                            ),
                            rx.text("th.t", size="1"),
                            spacing="1",
                        ),
                        color_scheme="blue",
                        size="1",
                    ),
                    rx.button(
                        rx.icon("download", size=14),
                        rx.text("Excel", size="1"),
                        on_click=ProductionState.download_current_year_q_excel,
                        size="1",
                        variant="soft",
                        color_scheme="green",
                    ),
                    spacing="2",
                    align="center",
                ),
                width="100%",
                align="center",
            ),
            rx.divider(),
            rx.cond(
                ProductionState.current_year_q_count > 0,
                rx.box(
                    rx.table.root(
                        summary_q_header(),
                        rx.table.body(
                            rx.foreach(
                                ProductionState.current_year_q_display_data,
                                summary_q_row
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
                ),
                rx.center(
                    rx.vstack(
                        rx.icon("inbox", size=32, color=rx.color("gray", 8)),
                        rx.text(
                            "No Q forecast data for current year",
                            size="2",
                            color=rx.color("gray", 10)
                        ),
                        spacing="2",
                        align="center",
                    ),
                    padding="2em",
                ),
            ),
            width="100%",
            spacing="3",
        ),
        padding="1em",
        width="100%",
    )


def next_year_q_table() -> rx.Component:
    """Q (cumulative) summary table for next year."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.hstack(
                    rx.icon("bar-chart-2", size=18, color=rx.color("purple", 9)),
                    rx.heading(
                        rx.cond(
                            ProductionState.is_oil_phase,
                            f"Qoil Forecast {ProductionState.next_year} (tons)",
                            f"Qliq Forecast {ProductionState.next_year} (tons)"
                        ),
                        size="4"
                    ),
                    spacing="2",
                    align="center",
                ),
                rx.spacer(),
                rx.hstack(
                    rx.badge(
                        rx.hstack(
                            rx.text("Completions:", size="1"),
                            rx.text(ProductionState.next_year_q_count, weight="bold", size="1"),
                            spacing="1",
                        ),
                        color_scheme="purple",
                        size="1",
                    ),
                    rx.badge(
                        rx.hstack(
                            rx.text("Total:", size="1"),
                            rx.cond(
                                ProductionState.is_oil_phase,
                                rx.text(
                                    ProductionState.next_year_total_qoil.to(int).to(str),
                                    weight="bold",
                                    size="1"
                                ),
                                rx.text(
                                    ProductionState.next_year_total_qliq.to(int).to(str),
                                    weight="bold",
                                    size="1"
                                ),
                            ),
                            rx.text("th.t", size="1"),
                            spacing="1",
                        ),
                        color_scheme="blue",
                        size="1",
                    ),
                    rx.button(
                        rx.icon("download", size=14),
                        rx.text("Excel", size="1"),
                        on_click=ProductionState.download_next_year_q_excel,
                        size="1",
                        variant="soft",
                        color_scheme="green",
                    ),
                    spacing="2",
                    align="center",
                ),
                width="100%",
                align="center",
            ),
            rx.divider(),
            rx.cond(
                ProductionState.next_year_q_count > 0,
                rx.box(
                    rx.table.root(
                        summary_q_header(),
                        rx.table.body(
                            rx.foreach(
                                ProductionState.next_year_q_display_data,
                                summary_q_row
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
                ),
                rx.center(
                    rx.vstack(
                        rx.icon("inbox", size=32, color=rx.color("gray", 8)),
                        rx.text(
                            "No Q forecast data for next year",
                            size="2",
                            color=rx.color("gray", 10)
                        ),
                        spacing="2",
                        align="center",
                    ),
                    padding="2em",
                ),
            ),
            width="100%",
            spacing="3",
        ),
        padding="1em",
        width="100%",
    )


def rate_summary_section() -> rx.Component:
    """Section containing rate summary tables for both years."""
    return rx.vstack(
        rx.hstack(
            rx.hstack(
                rx.icon("activity", size=20, color=rx.color("blue", 9)),
                rx.heading("Production Rate Summary", size="5"),
                spacing="2",
                align="center",
            ),
            rx.spacer(),
            phase_selector(),
            rx.button(
                rx.icon("file-spreadsheet", size=16),
                rx.text("Download All", size="2"),
                on_click=ProductionState.download_all_summary_excel,
                size="2",
                variant="soft",
                color_scheme="blue",
            ),
            width="100%",
            align="center",
        ),
        rx.divider(),
        rx.grid(
            current_year_rate_table(),
            next_year_rate_table(),
            columns="2",
            spacing="4",
            width="100%",
        ),
        width="100%",
        spacing="4",
    )


def q_summary_section() -> rx.Component:
    """Section containing Q (cumulative) summary tables for both years."""
    return rx.vstack(
        rx.hstack(
            rx.hstack(
                rx.icon("bar-chart-2", size=20, color=rx.color("green", 9)),
                rx.heading("Cumulative Production (Q) Summary", size="5"),
                spacing="2",
                align="center",
            ),
            rx.spacer(),
            phase_selector(),
            width="100%",
            align="center",
        ),
        rx.divider(),
        rx.grid(
            current_year_q_table(),
            next_year_q_table(),
            columns="2",
            spacing="4",
            width="100%",
        ),
        width="100%",
        spacing="4",
    )


def production_summary_section() -> rx.Component:
    """Combined section showing both Rate and Q summary tables."""
    return rx.vstack(
        # Header with phase selector
        rx.hstack(
            rx.hstack(
                rx.icon("table-2", size=20, color=rx.color("blue", 9)),
                rx.heading("Production Forecast Summary", size="5"),
                spacing="2",
                align="center",
            ),
            rx.spacer(),
            phase_selector(),
            rx.button(
                rx.icon("file-spreadsheet", size=16),
                rx.text("Download All", size="2"),
                on_click=ProductionState.download_all_summary_excel,
                size="2",
                variant="soft",
                color_scheme="blue",
            ),
            width="100%",
            align="center",
        ),
        rx.divider(),
        
        # Rate Tables Section
        rx.vstack(
            rx.text("Rate Forecast (t/day)", size="3", weight="bold", color=rx.color("gray", 11)),
            rx.grid(
                current_year_rate_table(),
                next_year_rate_table(),
                columns="2",
                spacing="4",
                width="100%",
            ),
            width="100%",
            spacing="2",
        ),
        
        # Q Tables Section
        rx.vstack(
            rx.text("Cumulative Production (tons)", size="3", weight="bold", color=rx.color("gray", 11)),
            rx.grid(
                current_year_q_table(),
                next_year_q_table(),
                columns="2",
                spacing="4",
                width="100%",
            ),
            width="100%",
            spacing="2",
        ),
        
        width="100%",
        spacing="4",
    )