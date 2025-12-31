"""Production Summary Page.

Displays merged history and forecast data in a monthly summary table.
Features:
- Year selector (2025-2050)
- Metric selector (Rate/Q)
- Phase selector (Oil/Liquid)
- Table with UniqueId and 12 monthly columns
- Data from HistoryProd for past months, ProductionForecast for future months
- Excel download capability
"""
import reflex as rx
from ..states.summary_state import SummaryState
from ..templates import template


def year_selector() -> rx.Component:
    """Year selection dropdown."""
    return rx.vstack(
        rx.text("Year:", size="2", weight="bold"),
        rx.select(
            SummaryState.year_options,
            value=SummaryState.current_year_str,
            on_change=SummaryState.set_selected_year,
            size="2",
            width="120px",
        ),
        spacing="1",
        align="start",
    )


def metric_selector() -> rx.Component:
    """Metric selection (Rate/Q)."""
    return rx.vstack(
        rx.text("Metric:", size="2", weight="bold"),
        rx.select(
            SummaryState.metric_options,
            value=SummaryState.selected_metric,
            on_change=SummaryState.set_selected_metric,
            size="2",
            width="120px",
        ),
        spacing="1",
        align="start",
    )


def phase_selector() -> rx.Component:
    """Phase selection (Oil/Liquid)."""
    return rx.vstack(
        rx.text("Phase:", size="2", weight="bold"),
        rx.select(
            SummaryState.phase_options,
            value=SummaryState.selected_phase,
            on_change=SummaryState.set_selected_phase,
            size="2",
            width="120px",
        ),
        spacing="1",
        align="start",
    )


def filter_controls() -> rx.Component:
    """Filter controls section."""
    return rx.hstack(
        year_selector(),
        metric_selector(),
        phase_selector(),
        rx.spacer(),
        rx.button(
            rx.icon("refresh-cw", size=14),
            rx.text("Refresh", size="2"),
            on_click=SummaryState.load_summary_data,
            size="2",
            variant="soft",
        ),
        rx.button(
            rx.icon("download", size=14),
            rx.text("Download Excel", size="2"),
            on_click=SummaryState.download_summary_excel,
            size="2",
            color_scheme="green",
        ),
        spacing="4",
        align="end",
        width="100%",
        padding="1em",
    )


def summary_table_header() -> rx.Component:
    """Table header with month columns."""
    columns = [
        ("UniqueId", "120px"),
        ("Well", "100px"),
        ("Field", "80px"),
        ("Platform", "80px"),
        ("Reservoir", "80px"),
        ("VSP%", "60px"),
        ("Jan", "55px"),
        ("Feb", "55px"),
        ("Mar", "55px"),
        ("Apr", "55px"),
        ("May", "55px"),
        ("Jun", "55px"),
        ("Jul", "55px"),
        ("Aug", "55px"),
        ("Sep", "55px"),
        ("Oct", "55px"),
        ("Nov", "55px"),
        ("Dec", "55px"),
        ("Total", "80px"),
    ]
    
    return rx.table.header(
        rx.table.row(
            *[
                rx.table.column_header_cell(
                    rx.text(col[0], size="1", weight="bold"),
                    width=col[1],
                )
                for col in columns
            ],
            style={"bg": rx.color("gray", 2)},
        ),
    )


def summary_table_row(row: dict) -> rx.Component:
    """Render a single row in the summary table."""
    # Use rx.cond for Reflex state variable comparison
    is_total = row["UniqueId"] == "TOTAL"
    
    return rx.table.row(
        rx.table.cell(
            rx.cond(
                is_total,
                rx.text(row["UniqueId"], size="1", weight="bold"),
                rx.text(row["UniqueId"], size="1", weight="medium"),
            ),
        ),
        rx.table.cell(
            rx.text(row["WellName"], size="1"),
        ),
        rx.table.cell(
            rx.text(row["Field"], size="1"),
        ),
        rx.table.cell(
            rx.text(row["Platform"], size="1"),
        ),
        rx.table.cell(
            rx.cond(
                is_total,
                rx.text("-", size="1"),
                rx.badge(row["Reservoir"], color_scheme="blue", size="1"),
            ),
        ),
        rx.table.cell(
            rx.cond(
                is_total,
                rx.text("-", size="1"),
                rx.badge(row["VSPShare"], color_scheme="purple", size="1"),
            ),
        ),
        # Monthly columns - use rx.cond for conditional rendering
        rx.table.cell(
            rx.cond(
                is_total,
                rx.badge(row["Jan"], color_scheme="green", size="1"),
                rx.text(row["Jan"], size="1"),
            ),
        ),
        rx.table.cell(
            rx.cond(
                is_total,
                rx.badge(row["Feb"], color_scheme="green", size="1"),
                rx.text(row["Feb"], size="1"),
            ),
        ),
        rx.table.cell(
            rx.cond(
                is_total,
                rx.badge(row["Mar"], color_scheme="green", size="1"),
                rx.text(row["Mar"], size="1"),
            ),
        ),
        rx.table.cell(
            rx.cond(
                is_total,
                rx.badge(row["Apr"], color_scheme="green", size="1"),
                rx.text(row["Apr"], size="1"),
            ),
        ),
        rx.table.cell(
            rx.cond(
                is_total,
                rx.badge(row["May"], color_scheme="green", size="1"),
                rx.text(row["May"], size="1"),
            ),
        ),
        rx.table.cell(
            rx.cond(
                is_total,
                rx.badge(row["Jun"], color_scheme="green", size="1"),
                rx.text(row["Jun"], size="1"),
            ),
        ),
        rx.table.cell(
            rx.cond(
                is_total,
                rx.badge(row["Jul"], color_scheme="green", size="1"),
                rx.text(row["Jul"], size="1"),
            ),
        ),
        rx.table.cell(
            rx.cond(
                is_total,
                rx.badge(row["Aug"], color_scheme="green", size="1"),
                rx.text(row["Aug"], size="1"),
            ),
        ),
        rx.table.cell(
            rx.cond(
                is_total,
                rx.badge(row["Sep"], color_scheme="green", size="1"),
                rx.text(row["Sep"], size="1"),
            ),
        ),
        rx.table.cell(
            rx.cond(
                is_total,
                rx.badge(row["Oct"], color_scheme="green", size="1"),
                rx.text(row["Oct"], size="1"),
            ),
        ),
        rx.table.cell(
            rx.cond(
                is_total,
                rx.badge(row["Nov"], color_scheme="green", size="1"),
                rx.text(row["Nov"], size="1"),
            ),
        ),
        rx.table.cell(
            rx.cond(
                is_total,
                rx.badge(row["Dec"], color_scheme="green", size="1"),
                rx.text(row["Dec"], size="1"),
            ),
        ),
        rx.table.cell(
            rx.cond(
                is_total,
                rx.badge(row["Total"], color_scheme="blue", size="1", variant="solid"),
                rx.badge(row["Total"], color_scheme="green", size="1", variant="solid"),
            ),
        ),
        style={"_hover": {"bg": rx.color("gray", 3)}},
        align="center",
    )


def summary_table() -> rx.Component:
    """Main summary table component."""
    return rx.cond(
        SummaryState.is_loading,
        rx.center(
            rx.vstack(
                rx.spinner(size="3"),
                rx.text("Loading data...", size="2", color=rx.color("gray", 10)),
                spacing="2",
            ),
            padding="4em",
        ),
        rx.cond(
            SummaryState.summary_count > 0,
            rx.box(
                rx.table.root(
                    summary_table_header(),
                    rx.table.body(
                        rx.foreach(
                            SummaryState.summary_data,
                            summary_table_row
                        ),
                    ),
                    variant="surface",
                    size="1",
                    width="100%",
                ),
                overflow_x="auto",
                overflow_y="auto",
                max_height="600px",
                width="100%",
            ),
            rx.center(
                rx.vstack(
                    rx.icon("inbox", size=48, color=rx.color("gray", 8)),
                    rx.text(
                        "No data available for selected filters",
                        size="3",
                        color=rx.color("gray", 10)
                    ),
                    rx.text(
                        "Try selecting a different year or run forecasts first",
                        size="2",
                        color=rx.color("gray", 9)
                    ),
                    spacing="2",
                    align="center",
                ),
                padding="4em",
            ),
        ),
    )


def stats_badges() -> rx.Component:
    """Display summary statistics."""
    return rx.hstack(
        rx.badge(
            rx.hstack(
                rx.icon("layers", size=12),
                rx.text(f"Records: {SummaryState.summary_count}", size="1"),
                spacing="1",
            ),
            color_scheme="blue",
            size="2",
        ),
        rx.badge(
            rx.hstack(
                rx.icon("sigma", size=12),
                rx.text(f"Total: {SummaryState.total_value}", size="1"),
                spacing="1",
            ),
            color_scheme="green",
            size="2",
        ),
        spacing="2",
    )


@template(
    route="/summary",
    title="Summary | Production Dashboard",
    description="History and Forecast Summary",
    on_load=SummaryState.load_summary_data,
)
def summary_page() -> rx.Component:
    """Production Summary Page.
    
    Displays merged history and forecast data in monthly format.
    - Past months: Data from HistoryProd table
    - Future months: Data from ProductionForecast table
    """
    return rx.vstack(
        # Page Header
        rx.hstack(
            rx.vstack(
                rx.heading("Production Summary", size="6"),
                rx.text(
                    "History + Forecast monthly data",
                    size="2",
                    color=rx.color("gray", 10),
                ),
                spacing="1",
                align="start",
            ),
            rx.spacer(),
            stats_badges(),
            width="100%",
            align="center",
        ),
        rx.divider(),
        
        # Filter Controls
        rx.card(
            filter_controls(),
            width="100%",
        ),
        
        # Summary Table
        rx.card(
            rx.vstack(
                rx.hstack(
                    rx.hstack(
                        rx.icon("table-2", size=18, color=rx.color("blue", 9)),
                        rx.heading(SummaryState.table_title, size="4"),
                        spacing="2",
                        align="center",
                    ),
                    rx.spacer(),
                    rx.text(
                        "* Past months from history, future months from forecast",
                        size="1",
                        color=rx.color("gray", 9),
                        style={"font-style": "italic"},
                    ),
                    width="100%",
                    align="center",
                ),
                rx.divider(),
                summary_table(),
                width="100%",
                spacing="3",
            ),
            padding="1em",
            width="100%",
        ),
        
        align="start",
        spacing="4",
        width="100%",
        padding="1em",
    )