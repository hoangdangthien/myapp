"""Block Summary Components for Block 09-1 Production Summary.

Enhanced UI components with:
- History production breakdown
- VSP share display
- Intervention gain visualization
- Stacked bar chart for production breakdown
"""
import reflex as rx
import plotly.graph_objects as go
from ..states.summary_state import (
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
        
        # VSP Display
        rx.badge(
            BlockSummaryState.vsp_display,
            color_scheme="purple",
            size="2",
        ),
        
        # Download buttons
        rx.hstack(
            rx.button(
                rx.icon("download", size=14),
                rx.text("Table 1", size="1"),
                on_click=BlockSummaryState.download_current_year_excel,
                size="1",
                variant="soft",
            ),
            rx.button(
                rx.icon("download", size=14),
                rx.text("Table 2", size="1"),
                on_click=BlockSummaryState.download_next_year_excel,
                size="1",
                variant="soft",
            ),
            rx.button(
                rx.icon("download", size=14),
                rx.text("Detailed", size="1"),
                on_click=BlockSummaryState.download_detailed_excel,
                size="1",
                variant="soft",
            ),
            spacing="2",
        ),
        
        width="100%",
        spacing="3",
        align="center",
        wrap="wrap",
        padding="0.5em",
    )


def summary_row(row: dict) -> rx.Component:
    """Render a single row in the summary table."""
    category = row.get("category", "")
    color = row.get("color", "gray")
    
    # Use rx.match for category-based styling
    return rx.table.row(
        rx.table.cell(
            rx.hstack(
                rx.box(
                    width="12px",
                    height="12px",
                    bg=color,
                    border_radius="2px",
                    border="1px solid #ccc",
                ),
                rx.text(row.get("label", ""), size="1"),
                spacing="2",
            ),
        ),
        rx.foreach(
            MONTH_NAMES,
            lambda m: rx.table.cell(
                rx.text(
                    row[m],
                    size="1",
                ),
                align="right",
            )
        ),
        rx.table.cell(
            rx.text(
                row.get("Total", 0),
                size="1",
                weight="bold",
            ),
            align="right",
        ),
        style={
            "background_color": rx.match(
                category,
                ("total", rx.color("green", 3)),
                ("net_total", rx.color("green", 4)),
                ("intervention_total", rx.color("blue", 3)),
                ("tech_loss", rx.color("red", 2)),
                ("history", rx.color("blue", 2)),
                "transparent",
            ),
        },
    )


def current_year_summary_table() -> rx.Component:
    """Summary table for current year."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.heading(
                    f"Table 1: Summary {BlockSummaryState.selected_current_year}",
                    size="4",
                ),
                rx.spacer(),
                rx.badge(
                    f"Total: {BlockSummaryState.current_year_total} ng.tấn",
                    color_scheme="green",
                    size="2",
                ),
                width="100%",
                align="center",
            ),
            rx.divider(),
            rx.box(
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell(
                                rx.text("Category", size="1", weight="bold"),
                                width="200px",
                            ),
                            rx.foreach(
                                MONTH_NAMES,
                                lambda m: rx.table.column_header_cell(
                                    rx.text(m, size="1", weight="bold"),
                                    align="right",
                                )
                            ),
                            rx.table.column_header_cell(
                                rx.text("Total", size="1", weight="bold"),
                                align="right",
                            ),
                        ),
                    ),
                    rx.table.body(
                        rx.foreach(
                            BlockSummaryState.current_year_summary,
                            summary_row
                        ),
                    ),
                    variant="surface",
                    size="1",
                    width="100%",
                ),
                overflow_x="auto",
                width="100%",
            ),
            width="100%",
            spacing="2",
        ),
        padding="1em",
    )


def next_year_summary_table() -> rx.Component:
    """Summary table for next year."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.heading(
                    f"Table 2: Summary {BlockSummaryState.selected_next_year}",
                    size="4",
                ),
                rx.spacer(),
                rx.badge(
                    f"Total: {BlockSummaryState.next_year_total} ng.tấn",
                    color_scheme="orange",
                    size="2",
                ),
                width="100%",
                align="center",
            ),
            rx.divider(),
            rx.box(
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell(
                                rx.text("Category", size="1", weight="bold"),
                                width="200px",
                            ),
                            rx.foreach(
                                MONTH_NAMES,
                                lambda m: rx.table.column_header_cell(
                                    rx.text(m, size="1", weight="bold"),
                                    align="right",
                                )
                            ),
                            rx.table.column_header_cell(
                                rx.text("Total", size="1", weight="bold"),
                                align="right",
                            ),
                        ),
                    ),
                    rx.table.body(
                        rx.foreach(
                            BlockSummaryState.next_year_summary,
                            summary_row
                        ),
                    ),
                    variant="surface",
                    size="1",
                    width="100%",
                ),
                overflow_x="auto",
                width="100%",
            ),
            width="100%",
            spacing="2",
        ),
        padding="1em",
    )


def detailed_row(row: dict) -> rx.Component:
    """Render a single row in the detailed summary table."""
    row_type = row.get("row_type", "data")
    color = row.get("color", "")
    
    return rx.table.row(
        rx.table.cell(
            rx.hstack(
                rx.cond(
                    color != "",
                    rx.box(
                        width="12px",
                        height="12px",
                        bg=color,
                        border_radius="2px",
                        border="1px solid #ccc",
                    ),
                    rx.box(width="12px"),
                ),
                rx.text(
                    row.get("label", ""),
                    size="1",
                    weight=rx.match(
                        row_type,
                        ("header", "bold"),
                        ("subtotal", "bold"),
                        ("total", "bold"),
                        "normal",
                    ),
                ),
                spacing="2",
            ),
        ),
        rx.foreach(
            MONTH_NAMES,
            lambda m: rx.table.cell(
                rx.text(
                    row[m],
                    size="1",
                ),
                align="right",
            )
        ),
        rx.table.cell(
            rx.text(
                row.get("Total", ""),
                size="1",
                weight="bold",
            ),
            align="right",
        ),
        style={
            "background_color": rx.match(
                row_type,
                ("header", rx.color("gray", 3)),
                ("subtotal", rx.color("blue", 2)),
                ("total", rx.color("green", 3)),
                "transparent",
            ),
        },
    )


def detailed_summary_table() -> rx.Component:
    """Detailed breakdown table matching Excel format."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.heading("Detailed Production Breakdown", size="4"),
                rx.spacer(),
                rx.hstack(
                    rx.badge(
                        f"Intervention Gain: {BlockSummaryState.intervention_gain_next_year} ng.tấn",
                        color_scheme="blue",
                        size="2",
                    ),
                    spacing="2",
                ),
                width="100%",
                align="center",
            ),
            rx.divider(),
            rx.box(
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell(
                                rx.text("Category / Metric", size="1", weight="bold"),
                                width="250px",
                            ),
                            rx.foreach(
                                MONTH_NAMES,
                                lambda m: rx.table.column_header_cell(
                                    rx.text(m, size="1", weight="bold"),
                                    align="right",
                                )
                            ),
                            rx.table.column_header_cell(
                                rx.text("Total", size="1", weight="bold"),
                                align="right",
                            ),
                        ),
                    ),
                    rx.table.body(
                        rx.foreach(
                            BlockSummaryState.detailed_summary,
                            detailed_row
                        ),
                    ),
                    variant="surface",
                    size="1",
                    width="100%",
                ),
                overflow_x="auto",
                width="100%",
            ),
            width="100%",
            spacing="2",
        ),
        padding="1em",
    )


def history_summary_table() -> rx.Component:
    """History production summary table."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.icon("history", size=18, color=rx.color("blue", 9)),
                rx.heading("History Production Breakdown", size="4"),
                width="100%",
                align="center",
                spacing="2",
            ),
            rx.divider(),
            rx.box(
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell(
                                rx.text("Year", size="1", weight="bold"),
                                width="150px",
                            ),
                            rx.foreach(
                                MONTH_NAMES,
                                lambda m: rx.table.column_header_cell(
                                    rx.text(m, size="1", weight="bold"),
                                    align="right",
                                )
                            ),
                            rx.table.column_header_cell(
                                rx.text("Total", size="1", weight="bold"),
                                align="right",
                            ),
                        ),
                    ),
                    rx.table.body(
                        rx.foreach(
                            BlockSummaryState.history_summary,
                            lambda row: rx.table.row(
                                rx.table.cell(
                                    rx.text(row.get("label", ""), size="1", weight="bold"),
                                ),
                                rx.foreach(
                                    MONTH_NAMES,
                                    lambda m: rx.table.cell(
                                        rx.text(row[m], size="1"),
                                        align="right",
                                    )
                                ),
                                rx.table.cell(
                                    rx.text(
                                        row.get("Total", 0),
                                        size="1",
                                        weight="bold",
                                    ),
                                    align="right",
                                ),
                            )
                        ),
                    ),
                    variant="surface",
                    size="1",
                    width="100%",
                ),
                overflow_x="auto",
                width="100%",
            ),
            width="100%",
            spacing="2",
        ),
        padding="1em",
    )


def category_legend() -> rx.Component:
    """Legend showing category colors."""
    return rx.hstack(
        rx.foreach(
            [
                ("carryover", "Carryover", "white"),
                ("new_wells", "New Wells", "yellow"),
                ("sidetrack", "Sidetrack", "cyan"),
                ("reservoir_conversion", "Conversion", "orange"),
                ("hydraulic_frac", "Hydraulic Frac", "green"),
                ("esp", "ESP", "purple"),
                ("other", "Other", "pink"),
            ],
            lambda item: rx.hstack(
                rx.box(
                    width="12px",
                    height="12px",
                    bg=item[2],
                    border_radius="2px",
                    border="1px solid gray",
                ),
                rx.text(item[1], size="1"),
                spacing="1",
            )
        ),
        spacing="3",
        wrap="wrap",
    )


def summary_stats_cards() -> rx.Component:
    """Summary statistics cards."""
    return rx.grid(
        # Current Year Card
        rx.card(
            rx.vstack(
                rx.hstack(
                    rx.icon("calendar", size=16, color=rx.color("blue", 9)),
                    rx.text(
                        f"Year {BlockSummaryState.selected_current_year}",
                        size="2",
                        weight="bold",
                    ),
                    spacing="2",
                ),
                rx.heading(
                    f"{BlockSummaryState.current_year_total} ng.tấn",
                    size="5",
                    color=rx.color("blue", 11),
                ),
                rx.text(
                    f"Intervention Gain: {BlockSummaryState.intervention_gain_current_year} ng.tấn",
                    size="1",
                    color=rx.color("green", 10),
                ),
                spacing="1",
                align="start",
            ),
            padding="1em",
        ),
        
        # Next Year Card
        rx.card(
            rx.vstack(
                rx.hstack(
                    rx.icon("calendar-plus", size=16, color=rx.color("orange", 9)),
                    rx.text(
                        f"Year {BlockSummaryState.selected_next_year}",
                        size="2",
                        weight="bold",
                    ),
                    spacing="2",
                ),
                rx.heading(
                    f"{BlockSummaryState.next_year_total} ng.tấn",
                    size="5",
                    color=rx.color("orange", 11),
                ),
                rx.text(
                    f"Intervention Gain: {BlockSummaryState.intervention_gain_next_year} ng.tấn",
                    size="1",
                    color=rx.color("green", 10),
                ),
                spacing="1",
                align="start",
            ),
            padding="1em",
        ),
        
        # VSP Card
        rx.card(
            rx.vstack(
                rx.hstack(
                    rx.icon("percent", size=16, color=rx.color("purple", 9)),
                    rx.text("VSP Share", size="2", weight="bold"),
                    spacing="2",
                ),
                rx.heading(
                    f"{BlockSummaryState.total_vsp_share}%",
                    size="5",
                    color=rx.color("purple", 11),
                ),
                rx.text(
                    "Vietsovpetro Share",
                    size="1",
                    color=rx.color("gray", 10),
                ),
                spacing="1",
                align="start",
            ),
            padding="1em",
        ),
        
        # Technical Loss Card
        rx.card(
            rx.vstack(
                rx.hstack(
                    rx.icon("trending-down", size=16, color=rx.color("red", 9)),
                    rx.text("Technical Loss", size="2", weight="bold"),
                    spacing="2",
                ),
                rx.heading(
                    f"{BlockSummaryState.technical_loss_percent}%",
                    size="5",
                    color=rx.color("red", 11),
                ),
                rx.text(
                    "Applied to gross production",
                    size="1",
                    color=rx.color("gray", 10),
                ),
                spacing="1",
                align="start",
            ),
            padding="1em",
        ),
        
        columns="4",
        spacing="3",
        width="100%",
    )


def production_breakdown_chart() -> rx.Component:
    """Stacked bar chart showing production breakdown by category."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.icon("bar-chart-2", size=18, color=rx.color("green", 9)),
                rx.heading("Production Breakdown by Category", size="4"),
                width="100%",
                align="center",
                spacing="2",
            ),
            rx.divider(),
            rx.plotly(
                data=BlockSummaryState.production_breakdown_chart_data,
                width="100%",
                height="400px",
                config={"displayModeBar": False},
            ),
            width="100%",
            spacing="2",
        ),
        padding="1em",
    )


# Add computed property for chart data in state
def get_production_breakdown_chart_data(state: BlockSummaryState) -> go.Figure:
    """Generate stacked bar chart for production breakdown."""
    fig = go.Figure()
    
    # Get data from summary
    categories = [
        ("carryover", "Carryover", "#FFFFFF"),
        ("new_wells", "New Wells", "#FFFF00"),
        ("sidetrack", "Sidetrack", "#00FFFF"),
        ("reservoir_conversion", "Conversion", "#FFA500"),
        ("hydraulic_frac", "Hydraulic Frac", "#00FF00"),
        ("esp", "ESP", "#800080"),
        ("other", "Other", "#FFC0CB"),
    ]
    
    # Create traces for each category
    for cat_key, cat_name, cat_color in categories:
        values = []
        for row in state.current_year_summary:
            if row.get("category") == cat_key:
                for m in MONTH_NAMES:
                    values.append(row.get(m, 0))
                break
        
        if values:
            fig.add_trace(go.Bar(
                name=cat_name,
                x=MONTH_NAMES,
                y=values,
                marker_color=cat_color,
                marker_line_color="gray",
                marker_line_width=1,
            ))
    
    fig.update_layout(
        barmode='stack',
        title="Monthly Production by Category",
        xaxis_title="Month",
        yaxis_title="Production (ng.tấn)",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        margin=dict(l=50, r=50, t=50, b=50),
    )
    
    return fig