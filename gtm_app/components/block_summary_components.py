"""Block Summary Components for Block 09-1 Production Summary.

UI components for displaying production summary by intervention category.
Includes summary tables, controls, and chart components.
"""
import reflex as rx
from ..states.block_summary_state import (
    BlockSummaryState, 
    MONTH_NAMES, 
    CATEGORY_LABELS,
    CATEGORY_COLORS,
)


def block_summary_controls() -> rx.Component:
    """Control bar for phase selection, year selection, and technical loss."""
    return rx.hstack(
        # Phase selector
        rx.hstack(
            rx.text("Phase:", size="2", weight="bold"),
            rx.select(
                ["oil", "liquid"],
                value=BlockSummaryState.selected_phase,
                on_change=BlockSummaryState.set_selected_phase,
                size="1",
            ),
            spacing="2",
            align="center",
        ),
        
        rx.divider(orientation="vertical", size="2"),
        
        # Current year selector
        rx.hstack(
            rx.text("Table 1 Year:", size="2", weight="bold"),
            rx.select(
                BlockSummaryState.available_years,
                value=BlockSummaryState.selected_current_year.to(str),
                on_change=BlockSummaryState.set_current_year,
                size="1",
                width="100px",
            ),
            spacing="2",
            align="center",
        ),
        
        # Next year selector
        rx.hstack(
            rx.text("Table 2 Year:", size="2", weight="bold"),
            rx.select(
                BlockSummaryState.available_years,
                value=BlockSummaryState.selected_next_year.to(str),
                on_change=BlockSummaryState.set_next_year,
                size="1",
                width="100px",
            ),
            spacing="2",
            align="center",
        ),
        
        rx.divider(orientation="vertical", size="2"),
        
        # Technical loss input
        rx.hstack(
            rx.text("Tech Loss %:", size="2", weight="bold"),
            rx.input(
                value=BlockSummaryState.technical_loss_percent.to(str),
                on_change=BlockSummaryState.set_technical_loss,
                type="number",
                size="1",
                width="80px",
            ),
            spacing="2",
            align="center",
        ),
        
        rx.spacer(),
        
        # Download buttons
        rx.hstack(
            rx.button(
                rx.icon("download", size=14),
                rx.text("Table 1", size="1"),
                on_click=BlockSummaryState.download_current_year_excel,
                size="1",
                variant="soft",
                color_scheme="green",
            ),
            rx.button(
                rx.icon("download", size=14),
                rx.text("Table 2", size="1"),
                on_click=BlockSummaryState.download_next_year_excel,
                size="1",
                variant="soft",
                color_scheme="blue",
            ),
            rx.button(
                rx.icon("file-spreadsheet", size=14),
                rx.text("Detailed", size="1"),
                on_click=BlockSummaryState.download_detailed_excel,
                size="1",
                variant="soft",
                color_scheme="purple",
            ),
            spacing="2",
        ),
        
        width="100%",
        padding="0.5em",
        spacing="4",
        align="center",
        wrap="wrap",
    )


def summary_table_header() -> rx.Component:
    """Header row for summary tables."""
    return rx.table.header(
        rx.table.row(
            rx.table.column_header_cell(
                rx.text("Category", size="1", weight="bold"),
                width="200px",
            ),
            *[
                rx.table.column_header_cell(
                    rx.text(m, size="1", weight="bold"),
                    width="60px",
                )
                for m in MONTH_NAMES
            ],
            rx.table.column_header_cell(
                rx.text("Total", size="1", weight="bold"),
                width="80px",
            ),
        ),
    )


def summary_table_row(row: dict) -> rx.Component:
    """Render a single row in the summary table.
    
    Uses rx.cond for conditional styling based on category type.
    """
    # Get category from row - this is a Var
    category = row["category"]
    
    # Check if this is a total-type row using bitwise OR (|) operator
    is_total_row = (
        (category == "total") | 
        (category == "intervention_total") | 
        (category == "net_total") | 
        (category == "tech_loss")
    )
    
    return rx.table.row(
        rx.table.cell(
            rx.hstack(
                rx.cond(
                    category != "carryover",
                    rx.box(
                        width="12px",
                        height="12px",
                        border_radius="2px",
                        background=row["color"],
                    ),
                    rx.fragment(),
                ),
                rx.text(
                    row["label"], 
                    size="1", 
                    weight=rx.cond(is_total_row, "bold", "medium"),
                ),
                spacing="2",
                align="center",
            ),
        ),
        # Monthly columns
        rx.table.cell(
            rx.text(
                rx.cond(row["Jan"] != 0, row["Jan"], "-"),
                size="1",
                weight=rx.cond(is_total_row, "bold", "normal"),
            )
        ),
        rx.table.cell(
            rx.text(
                rx.cond(row["Feb"] != 0, row["Feb"], "-"),
                size="1",
                weight=rx.cond(is_total_row, "bold", "normal"),
            )
        ),
        rx.table.cell(
            rx.text(
                rx.cond(row["Mar"] != 0, row["Mar"], "-"),
                size="1",
                weight=rx.cond(is_total_row, "bold", "normal"),
            )
        ),
        rx.table.cell(
            rx.text(
                rx.cond(row["Apr"] != 0, row["Apr"], "-"),
                size="1",
                weight=rx.cond(is_total_row, "bold", "normal"),
            )
        ),
        rx.table.cell(
            rx.text(
                rx.cond(row["May"] != 0, row["May"], "-"),
                size="1",
                weight=rx.cond(is_total_row, "bold", "normal"),
            )
        ),
        rx.table.cell(
            rx.text(
                rx.cond(row["Jun"] != 0, row["Jun"], "-"),
                size="1",
                weight=rx.cond(is_total_row, "bold", "normal"),
            )
        ),
        rx.table.cell(
            rx.text(
                rx.cond(row["Jul"] != 0, row["Jul"], "-"),
                size="1",
                weight=rx.cond(is_total_row, "bold", "normal"),
            )
        ),
        rx.table.cell(
            rx.text(
                rx.cond(row["Aug"] != 0, row["Aug"], "-"),
                size="1",
                weight=rx.cond(is_total_row, "bold", "normal"),
            )
        ),
        rx.table.cell(
            rx.text(
                rx.cond(row["Sep"] != 0, row["Sep"], "-"),
                size="1",
                weight=rx.cond(is_total_row, "bold", "normal"),
            )
        ),
        rx.table.cell(
            rx.text(
                rx.cond(row["Oct"] != 0, row["Oct"], "-"),
                size="1",
                weight=rx.cond(is_total_row, "bold", "normal"),
            )
        ),
        rx.table.cell(
            rx.text(
                rx.cond(row["Nov"] != 0, row["Nov"], "-"),
                size="1",
                weight=rx.cond(is_total_row, "bold", "normal"),
            )
        ),
        rx.table.cell(
            rx.text(
                rx.cond(row["Dec"] != 0, row["Dec"], "-"),
                size="1",
                weight=rx.cond(is_total_row, "bold", "normal"),
            )
        ),
        # Total column
        rx.table.cell(
            rx.badge(
                row["Total"],
                color_scheme=rx.cond(is_total_row, "green", "gray"),
                size="1",
                variant=rx.cond(is_total_row, "solid", "soft"),
            )
        ),
        style={
            "_hover": {"bg": rx.color("gray", 3)},
        },
        background=rx.cond(
            is_total_row,
            rx.color("green", 2),
            "transparent",
        ),
        align="center",
    )


def current_year_summary_table() -> rx.Component:
    """Table 1: Current year summary by category."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.hstack(
                    rx.icon("calendar", size=18, color=rx.color("blue", 9)),
                    rx.heading(
                        rx.cond(
                            BlockSummaryState.is_oil_phase,
                            f"Qoil Summary {BlockSummaryState.selected_current_year} (ng.tấn)",
                            f"Qliq Summary {BlockSummaryState.selected_current_year} (ng.tấn)",
                        ),
                        size="4"
                    ),
                    spacing="2",
                    align="center",
                ),
                rx.spacer(),
                rx.badge(
                    rx.hstack(
                        rx.text("Total:", size="1"),
                        rx.text(
                            BlockSummaryState.current_year_total_q.to(int).to(str),
                            weight="bold",
                            size="1"
                        ),
                        rx.text("ng.t", size="1"),
                        spacing="1",
                    ),
                    color_scheme="blue",
                    size="1",
                ),
                width="100%",
                align="center",
            ),
            rx.divider(),
            rx.cond(
                BlockSummaryState.current_year_summary.length() > 0,
                rx.box(
                    rx.table.root(
                        summary_table_header(),
                        rx.table.body(
                            rx.foreach(
                                BlockSummaryState.current_year_summary,
                                summary_table_row,
                            ),
                        ),
                        variant="surface",
                        size="1",
                        width="100%",
                    ),
                    overflow_x="auto",
                    overflow_y="auto",
                    max_height="400px",
                    width="100%",
                ),
                rx.center(
                    rx.vstack(
                        rx.icon("inbox", size=32, color=rx.color("gray", 8)),
                        rx.text(
                            "No data available",
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
    """Table 2: Next year summary by category."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.hstack(
                    rx.icon("calendar-plus", size=18, color=rx.color("orange", 9)),
                    rx.heading(
                        rx.cond(
                            BlockSummaryState.is_oil_phase,
                            f"Qoil Summary {BlockSummaryState.selected_next_year} (ng.tấn)",
                            f"Qliq Summary {BlockSummaryState.selected_next_year} (ng.tấn)",
                        ),
                        size="4"
                    ),
                    spacing="2",
                    align="center",
                ),
                rx.spacer(),
                rx.badge(
                    rx.hstack(
                        rx.text("Total:", size="1"),
                        rx.text(
                            BlockSummaryState.next_year_total_q.to(int).to(str),
                            weight="bold",
                            size="1"
                        ),
                        rx.text("ng.t", size="1"),
                        spacing="1",
                    ),
                    color_scheme="orange",
                    size="1",
                ),
                width="100%",
                align="center",
            ),
            rx.divider(),
            rx.cond(
                BlockSummaryState.next_year_summary.length() > 0,
                rx.box(
                    rx.table.root(
                        summary_table_header(),
                        rx.table.body(
                            rx.foreach(
                                BlockSummaryState.next_year_summary,
                                summary_table_row,
                            ),
                        ),
                        variant="surface",
                        size="1",
                        width="100%",
                    ),
                    overflow_x="auto",
                    overflow_y="auto",
                    max_height="400px",
                    width="100%",
                ),
                rx.center(
                    rx.vstack(
                        rx.icon("inbox", size=32, color=rx.color("gray", 8)),
                        rx.text(
                            "No data available",
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


def detailed_table_header() -> rx.Component:
    """Header for detailed breakdown table (like Excel image)."""
    return rx.table.header(
        rx.table.row(
            rx.table.column_header_cell(
                rx.text("Thông số", size="1", weight="bold"),
                width="250px",
            ),
            *[
                rx.table.column_header_cell(
                    rx.text(str(i), size="1", weight="bold"),
                    width="50px",
                )
                for i in range(1, 13)
            ],
            rx.table.column_header_cell(
                rx.text(BlockSummaryState.selected_next_year, size="1", weight="bold"),
                width="70px",
            ),
        ),
    )


def detailed_table_row(row: dict) -> rx.Component:
    """Render a row in the detailed breakdown table."""
    row_type = row["row_type"]
    color = row["color"]
    
    # Style based on row type using bitwise OR (|) operator
    is_header = row_type == "header"
    is_total = (
        (row_type == "total") | 
        (row_type == "subtotal") | 
        (row_type == "net") | 
        (row_type == "loss")
    )
    is_styled = is_header | is_total
    
    return rx.table.row(
        rx.table.cell(
            rx.text(
                row["label"], 
                size="1", 
                weight=rx.cond(is_styled, "bold", "normal"),
            ),
        ),
        # Monthly columns (1-12)
        rx.table.cell(rx.text(row["Jan"], size="1", weight=rx.cond(is_styled, "bold", "normal"))),
        rx.table.cell(rx.text(row["Feb"], size="1", weight=rx.cond(is_styled, "bold", "normal"))),
        rx.table.cell(rx.text(row["Mar"], size="1", weight=rx.cond(is_styled, "bold", "normal"))),
        rx.table.cell(rx.text(row["Apr"], size="1", weight=rx.cond(is_styled, "bold", "normal"))),
        rx.table.cell(rx.text(row["May"], size="1", weight=rx.cond(is_styled, "bold", "normal"))),
        rx.table.cell(rx.text(row["Jun"], size="1", weight=rx.cond(is_styled, "bold", "normal"))),
        rx.table.cell(rx.text(row["Jul"], size="1", weight=rx.cond(is_styled, "bold", "normal"))),
        rx.table.cell(rx.text(row["Aug"], size="1", weight=rx.cond(is_styled, "bold", "normal"))),
        rx.table.cell(rx.text(row["Sep"], size="1", weight=rx.cond(is_styled, "bold", "normal"))),
        rx.table.cell(rx.text(row["Oct"], size="1", weight=rx.cond(is_styled, "bold", "normal"))),
        rx.table.cell(rx.text(row["Nov"], size="1", weight=rx.cond(is_styled, "bold", "normal"))),
        rx.table.cell(rx.text(row["Dec"], size="1", weight=rx.cond(is_styled, "bold", "normal"))),
        # Total column
        rx.table.cell(
            rx.cond(
                row["Total"] != "",
                rx.badge(
                    row["Total"],
                    color_scheme=rx.cond(is_total, "green", "gray"),
                    size="1",
                ),
                rx.text("", size="1"),
            )
        ),
        # Apply background color based on row color using nested rx.cond
        background=rx.cond(
            color == "yellow",
            "#FFFDE7",
            rx.cond(
                color == "cyan",
                "#E0F7FA",
                rx.cond(
                    color == "orange",
                    "#FFF3E0",
                    rx.cond(
                        color == "green",
                        "#E8F5E9",
                        rx.cond(
                            color == "purple",
                            "#F3E5F5",
                            rx.cond(
                                color == "pink",
                                "#FCE4EC",
                                rx.cond(
                                    color == "lightblue",
                                    "#E3F2FD",
                                    rx.cond(
                                        color == "lightgreen",
                                        "#C8E6C9",
                                        "transparent",
                                    ),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        ),
        align="center",
    )


def detailed_summary_table() -> rx.Component:
    """Table 3: Detailed breakdown matching Excel format."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.hstack(
                    rx.icon("table-2", size=18, color=rx.color("purple", 9)),
                    rx.heading(
                        f"ДОБЫЧА БЛОКА 09-1 {BlockSummaryState.selected_next_year}",
                        size="4"
                    ),
                    spacing="2",
                    align="center",
                ),
                rx.spacer(),
                rx.button(
                    rx.icon("download", size=14),
                    rx.text("Download Excel", size="1"),
                    on_click=BlockSummaryState.download_detailed_excel,
                    size="1",
                    variant="soft",
                    color_scheme="purple",
                ),
                width="100%",
                align="center",
            ),
            rx.divider(),
            rx.cond(
                BlockSummaryState.detailed_summary.length() > 0,
                rx.box(
                    rx.table.root(
                        detailed_table_header(),
                        rx.table.body(
                            rx.foreach(
                                BlockSummaryState.detailed_summary,
                                detailed_table_row,
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
                        rx.icon("inbox", size=32, color=rx.color("gray", 8)),
                        rx.text(
                            "No detailed data available",
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



def category_legend() -> rx.Component:
    """Legend showing category colors."""
    categories = [
        ("carryover", "Carryover Wells", "#E8E8E8"),
        ("new_wells", "New/Infill Wells", "#FFEB3B"),
        ("sidetrack", "Sidetrack Wells", "#00BCD4"),
        ("reservoir_conversion", "Reservoir Conversion", "#FF9800"),
        ("hydraulic_frac", "Hydraulic Fracturing", "#4CAF50"),
        ("esp", "ESP Installation", "#9C27B0"),
        ("other", "Other Workover", "#E91E63"),
    ]
    
    return rx.hstack(
        *[
            rx.hstack(
                rx.box(
                    width="16px",
                    height="16px",
                    border_radius="4px",
                    background=color,
                    border="1px solid #ccc",
                ),
                rx.text(label, size="1"),
                spacing="1",
                align="center",
            )
            for cat, label, color in categories
        ],
        wrap="wrap",
        spacing="4",
        justify="center",
        padding="0.5em",
    )