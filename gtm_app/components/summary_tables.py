"""Summary table components for Intervention Qoil forecast."""
import reflex as rx
from ..states.gtm_state import GTMState


def summary_table_row(row: dict) -> rx.Component:
    """Render a single row in the summary table."""
    return rx.table.row(
        rx.table.cell(rx.text(row["UniqueId"], size="1", weight="medium")),
        rx.table.cell(rx.text(row["Field"], size="1")),
        rx.table.cell(rx.text(row["Platform"], size="1")),
        rx.table.cell(rx.badge(row["Reservoir"], color_scheme="blue", size="1")),
        rx.table.cell(rx.badge(row["Type"], color_scheme="purple", size="1")),
        rx.table.cell(rx.text(row["Category"], size="1")),
        rx.table.cell(
            rx.badge(
                row["Status"],
                color_scheme=rx.cond(
                    row["Status"] == "Done", 
                    "green", 
                    rx.cond(row["Status"] == "Plan", "yellow", "gray")
                ),
                size="1"
            )
        ),
        rx.table.cell(rx.text(row["Date"], size="1")),
        # Monthly Qoil columns
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


def summary_table_header() -> rx.Component:
    """Common header for summary tables."""
    return rx.table.header(
        rx.table.row(
            rx.table.column_header_cell(rx.text("UniqueId", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Field", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Platform", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Reservoir", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Type", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Category", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Status", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Date", size="1", weight="bold")),
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
            rx.table.column_header_cell(rx.text("Total", size="1", weight="bold")),
        ),
    )


def current_year_summary_table() -> rx.Component:
    """Summary table for current year Qoil forecast by intervention."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.hstack(
                    rx.icon("calendar", size=18, color=rx.color("blue", 9)),
                    rx.heading(f"Qoil Forecast {GTMState.current_year} (tons)", size="4"),
                    spacing="2",
                    align="center",
                ),
                rx.spacer(),
                rx.hstack(
                    rx.badge(
                        rx.hstack(
                            rx.text("Interventions:", size="1"),
                            rx.text(GTMState.current_year_count, weight="bold", size="1"),
                            spacing="1",
                        ),
                        color_scheme="blue",
                        size="1",
                    ),
                    rx.badge(
                        rx.hstack(
                            rx.text("Total Qoil:", size="1"),
                            rx.text(
                                GTMState.current_year_total_qoil.to(int).to(str),
                                weight="bold",
                                size="1"
                            ),
                            rx.text("t", size="1"),
                            spacing="1",
                        ),
                        color_scheme="green",
                        size="1",
                    ),
                    rx.button(
                        rx.icon("download", size=14),
                        rx.text("Excel", size="1"),
                        on_click=GTMState.download_current_year_excel,
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
                GTMState.current_year_count > 0,
                rx.box(
                    rx.table.root(
                        summary_table_header(),
                        rx.table.body(
                            rx.foreach(
                                GTMState.current_year_summary,
                                summary_table_row
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
                            "No forecast data for current year",
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


def next_year_summary_table() -> rx.Component:
    """Summary table for next year Qoil forecast by intervention."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.hstack(
                    rx.icon("calendar-plus", size=18, color=rx.color("orange", 9)),
                    rx.heading(f"Qoil Forecast {GTMState.next_year} (tons)", size="4"),
                    spacing="2",
                    align="center",
                ),
                rx.spacer(),
                rx.hstack(
                    rx.badge(
                        rx.hstack(
                            rx.text("Interventions:", size="1"),
                            rx.text(GTMState.next_year_count, weight="bold", size="1"),
                            spacing="1",
                        ),
                        color_scheme="orange",
                        size="1",
                    ),
                    rx.badge(
                        rx.hstack(
                            rx.text("Total Qoil:", size="1"),
                            rx.text(
                                GTMState.next_year_total_qoil.to(int).to(str),
                                weight="bold",
                                size="1"
                            ),
                            rx.text("t", size="1"),
                            spacing="1",
                        ),
                        color_scheme="green",
                        size="1",
                    ),
                    rx.button(
                        rx.icon("download", size=14),
                        rx.text("Excel", size="1"),
                        on_click=GTMState.download_next_year_excel,
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
                GTMState.next_year_count > 0,
                rx.box(
                    rx.table.root(
                        summary_table_header(),
                        rx.table.body(
                            rx.foreach(
                                GTMState.next_year_summary,
                                summary_table_row
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
                            "No forecast data for next year",
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


def download_all_button() -> rx.Component:
    """Button to download both years as single Excel file."""
    return rx.button(
        rx.icon("file-spreadsheet", size=16),
        rx.text("Download All Years", size="2"),
        on_click=GTMState.download_both_years_excel,
        size="2",
        variant="soft",
        color_scheme="blue",
    )


def summary_section() -> rx.Component:
    """Combined section showing both year summaries with download button."""
    return rx.vstack(
        rx.hstack(
            rx.heading("Intervention Qoil Forecast Summary", size="5"),
            rx.spacer(),
            download_all_button(),
            width="100%",
            align="center",
        ),
        rx.divider(),
        current_year_summary_table(),
        next_year_summary_table(),
        width="100%",
        spacing="4",
    )