"""Shared table components for Production and GTM pages.

These components provide consistent table styling and behavior
across the application.
"""
import reflex as rx
from typing import Callable, List


def production_table_header(columns: List[str]) -> rx.Component:
    """Create a standardized table header.
    
    Args:
        columns: List of column names
        
    Returns:
        Table header component
    """
    return rx.table.header(
        rx.table.row(
            *[
                rx.table.column_header_cell(
                    rx.text(col, size="1", weight="bold")
                )
                for col in columns
            ]
        )
    )


def wc_badge(wc_value: rx.Var, wc_display: rx.Var = None) -> rx.Component:
    """Create a Water Cut badge with color coding.
    
    Args:
        wc_value: Water cut value for color determination
        wc_display: Display value (optional, uses wc_value if not provided)
        
    Returns:
        Colored badge component
    """
    display = wc_display if wc_display is not None else wc_value
    return rx.badge(
        display,
        color_scheme=rx.cond(
            wc_value.to(float) > 80,
            "red",
            rx.cond(
                wc_value.to(float) > 50,
                "yellow",
                "green"
            )
        ),
        size="1"
    )


def status_badge(status: rx.Var) -> rx.Component:
    """Create a status badge with color coding.
    
    Args:
        status: Status value
        
    Returns:
        Colored badge component
    """
    return rx.badge(
        status,
        color_scheme=rx.cond(
            status == "Done",
            "green",
            rx.cond(
                status == "Plan",
                "yellow",
                "gray"
            )
        ),
        size="1"
    )


def scrollable_table_container(
    table_component: rx.Component,
    max_height: str = "250px"
) -> rx.Component:
    """Wrap a table in a scrollable container.
    
    Args:
        table_component: The table to wrap
        max_height: Maximum height before scrolling
        
    Returns:
        Scrollable container with table
    """
    return rx.box(
        table_component,
        overflow_y="auto",
        overflow_x="auto",
        max_height=max_height,
        width="100%",
    )


def history_table_row(row: dict) -> rx.Component:
    """Render a standardized history table row.
    
    Args:
        row: Row data with Date, OilRate, LiqRate, WC, WC_val
        
    Returns:
        Table row component
    """
    return rx.table.row(
        rx.table.cell(rx.text(row["Date"], size="1")),
        rx.table.cell(rx.text(row["OilRate"], size="1")),
        rx.table.cell(rx.text(row["LiqRate"], size="1")),
        rx.table.cell(wc_badge(row["WC_val"], row["WC"])),
        style={"_hover": {"bg": rx.color("gray", 3)}},
    )


def forecast_table_row(row: dict, show_cumulative: bool = True) -> rx.Component:
    """Render a standardized forecast table row.
    
    Args:
        row: Row data with Date, OilRate, LiqRate, WC, Qoil, Qliq
        show_cumulative: Whether to show cumulative columns
        
    Returns:
        Table row component
    """
    cells = [
        rx.table.cell(rx.text(row["Date"], size="1")),
        rx.table.cell(rx.text(row["OilRate"], size="1")),
        rx.table.cell(rx.text(row["LiqRate"], size="1")),
    ]
    
    if show_cumulative:
        cells.extend([
            rx.table.cell(rx.badge(row["Qoil"], color_scheme="green", size="1")),
            rx.table.cell(rx.badge(row["Qliq"], color_scheme="blue", size="1")),
        ])
    
    cells.append(rx.table.cell(wc_badge(row["WC_val"], row["WC"])))
    
    return rx.table.row(
        *cells,
        style={"_hover": {"bg": rx.color("blue", 2)}},
    )


def create_history_table(
    data: rx.Var,
    columns: List[str] = None
) -> rx.Component:
    """Create a standardized history table.
    
    Args:
        data: List of row data
        columns: Column names (default: Date, Oil Rate, Liq Rate, WC %)
        
    Returns:
        Complete table component
    """
    if columns is None:
        columns = ["Date", "Oil Rate", "Liq Rate", "WC %"]
    
    return rx.table.root(
        production_table_header(columns),
        rx.table.body(
            rx.foreach(data, history_table_row)
        ),
        variant="surface",
        size="1",
        width="100%",
    )


def create_forecast_table(
    data: rx.Var,
    show_cumulative: bool = True,
    columns: List[str] = None
) -> rx.Component:
    """Create a standardized forecast table.
    
    Args:
        data: List of row data
        show_cumulative: Whether to show Qoil/Qliq columns
        columns: Column names (auto-generated if not provided)
        
    Returns:
        Complete table component
    """
    if columns is None:
        columns = ["Date", "Oil Rate", "Liq Rate"]
        if show_cumulative:
            columns.extend(["Qoil (t)", "Qliq (t)"])
        columns.append("WC %")
    
    return rx.table.root(
        production_table_header(columns),
        rx.table.body(
            rx.foreach(
                data,
                lambda row: forecast_table_row(row, show_cumulative)
            )
        ),
        variant="surface",
        size="1",
        width="100%",
    )


def stats_info_card(
    title: str,
    value: rx.Var,
    icon: str,
    color_scheme: str = "blue"
) -> rx.Component:
    """Create a statistics info card.
    
    Args:
        title: Card title
        value: Display value
        icon: Lucide icon name
        color_scheme: Color scheme for icon
        
    Returns:
        Card component
    """
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.icon(icon, size=18, color=rx.color(color_scheme, 9)),
                rx.text(title, size="1", weight="bold"),
                spacing="2",
            ),
            rx.heading(value, size="5"),
            spacing="1",
            align="start",
        ),
        padding="1em",
    )


def version_selector(
    version_options: rx.Var,
    current_version: rx.Var,
    on_change: Callable,
    max_versions: int = 4,
    show_count: bool = True
) -> rx.Component:
    """Create a version selector component.
    
    Args:
        version_options: List of version strings (e.g., ["v1", "v2"])
        current_version: Current selected version display
        on_change: Callback when version changes
        max_versions: Maximum versions for count display
        show_count: Whether to show version count
        
    Returns:
        Version selector component
    """
    return rx.cond(
        version_options.length() > 0,
        rx.hstack(
            rx.text("Version:", size="1", weight="bold"),
            rx.select(
                version_options,
                value=current_version,
                on_change=on_change,
                size="1",
                width="70px",
            ),
            rx.cond(
                show_count,
                rx.badge(
                    f"{version_options.length()}/{max_versions}",
                    color_scheme="gray",
                    size="1",
                ),
                rx.fragment(),
            ),
            spacing="2",
            align="center",
        ),
        rx.text("No forecasts", size="1", color=rx.color("gray", 9)),
    )


def loading_spinner(is_loading: rx.Var, message: str = "Loading...") -> rx.Component:
    """Create a conditional loading spinner.
    
    Args:
        is_loading: Boolean var for loading state
        message: Loading message
        
    Returns:
        Conditional spinner component
    """
    return rx.cond(
        is_loading,
        rx.hstack(
            rx.spinner(size="2"),
            rx.text(message, size="2", color=rx.color("gray", 10)),
            spacing="2",
            align="center",
        ),
        rx.fragment(),
    )


def empty_state(
    icon: str = "inbox",
    message: str = "No data available"
) -> rx.Component:
    """Create an empty state placeholder.
    
    Args:
        icon: Lucide icon name
        message: Message to display
        
    Returns:
        Empty state component
    """
    return rx.center(
        rx.vstack(
            rx.icon(icon, size=32, color=rx.color("gray", 8)),
            rx.text(message, size="2", color=rx.color("gray", 10)),
            spacing="2",
            align="center",
        ),
        padding="2em",
    )