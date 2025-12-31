"""Block 09-1 Production Summary Page.

Summary page showing production forecast aggregated by intervention category:
- Table 1: Current year Qoil/Qliq summary by category
- Table 2: Next year Qoil/Qliq summary by category  
- Table 3: Detailed breakdown matching Russian Excel format

Categories:
- Carryover wells (base production without intervention)
- New wells / Infill wells
- Sidetrack wells
- Reservoir conversion
- Hydraulic fracturing
- ESP installation
- Other workover solutions

Features:
- Phase toggle (oil/liquid)
- Year selection
- Technical loss adjustment
- Excel download
- Stacked bar chart visualization
"""
import reflex as rx
from ..templates.template import template
from ..states.block_summary_state import BlockSummaryState
from ..components.block_summary_components import (
    block_summary_controls,
    current_year_summary_table,
    next_year_summary_table,
    detailed_summary_table,
    category_legend,
)


def page_header() -> rx.Component:
    """Page header with title and summary badges."""
    return rx.hstack(
        rx.hstack(
            rx.icon("building-2", size=28, color=rx.color("blue", 9)),
            rx.vstack(
                rx.heading("Block 09-1 Production Summary", size="6"),
                rx.text(
                    "Production forecast by intervention category",
                    size="2",
                    color=rx.color("gray", 10),
                ),
                spacing="0",
                align="start",
            ),
            spacing="3",
            align="center",
        ),
        rx.spacer(),
        rx.hstack(
            rx.badge(
                rx.hstack(
                    rx.icon("calendar", size=14),
                    rx.text(f"Current: {BlockSummaryState.selected_current_year}", size="1"),
                    spacing="1",
                ),
                color_scheme="blue",
                size="2",
            ),
            rx.badge(
                rx.hstack(
                    rx.icon("calendar-plus", size=14),
                    rx.text(f"Next: {BlockSummaryState.selected_next_year}", size="1"),
                    spacing="1",
                ),
                color_scheme="orange",
                size="2",
            ),
            rx.badge(
                rx.hstack(
                    rx.text(
                        rx.cond(
                            BlockSummaryState.is_oil_phase,
                            "Oil Phase",
                            "Liquid Phase",
                        ),
                        size="1"
                    ),
                    spacing="1",
                ),
                color_scheme=rx.cond(BlockSummaryState.is_oil_phase, "green", "purple"),
                size="2",
            ),
            spacing="2",
        ),
        width="100%",
        align="center",
        padding="0.5em",
    )


def summary_tables_section() -> rx.Component:
    """Section containing the two summary tables side by side."""
    return rx.grid(
        current_year_summary_table(),
        next_year_summary_table(),
        columns="2",
        spacing="4",
        width="100%",
    )


def detailed_section() -> rx.Component:
    """Section containing the detailed breakdown table."""
    return rx.vstack(
        rx.hstack(
            rx.heading("Detailed Production Breakdown", size="5"),
            rx.spacer(),
            category_legend(),
            width="100%",
            align="center",
        ),
        detailed_summary_table(),
        width="100%",
        spacing="3",
    )



@template(
    route="/block-summary",
    title="Block 09-1 Summary | Production Dashboard",
    description="Block 09-1 production summary by intervention category",
    on_load=BlockSummaryState.load_block_summary,
)
def block_summary_page() -> rx.Component:
    """Block 09-1 Production Summary Page.
    
    Layout:
    - Header with page title and summary badges
    - Controls bar (phase, year selection, technical loss)
    - Two summary tables side by side (current year, next year)
    - Chart showing production by category
    - Detailed breakdown table (Russian Excel format)
    """
    return rx.vstack(
        # Page header
        page_header(),
        rx.divider(),
        
        # Controls bar
        rx.card(
            block_summary_controls(),
            padding="0.5em",
            width="100%",
        ),
        
        # Loading indicator
        rx.cond(
            BlockSummaryState.is_loading,
            rx.center(
                rx.vstack(
                    rx.spinner(size="3"),
                    rx.text("Loading summary data...", size="2"),
                    spacing="2",
                    align="center",
                ),
                padding="2em",
            ),
            rx.fragment(),
        ),
        
        # Summary tables (Table 1 and Table 2)
        summary_tables_section(),
        
        rx.divider(),
        
        # Detailed breakdown (Table 3)
        detailed_section(),
        
        align="start",
        spacing="4",
        width="100%",
    )