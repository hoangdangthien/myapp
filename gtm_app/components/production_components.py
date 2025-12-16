"""Components for Production monitoring page."""
import reflex as rx
from ..states.base_state import BaseState


def connection_dialog() -> rx.Component:
    """Dialog for configuring MSSQL Server connection parameters."""
    return rx.dialog.root(
        rx.dialog.trigger(
            rx.button(
                rx.icon("settings", size=16),
                rx.text("Configure Connection", size="2"),
                variant="soft",
                size="2",
            ),
        ),
        rx.dialog.content(
            rx.dialog.title("Database Connection Settings"),
            rx.dialog.description("Configure MSSQL Server connection parameters"),
            rx.form(
                rx.vstack(
                    rx.flex(
                        rx.text("Server:", size="2", weight="bold"),
                        rx.input(
                            placeholder="localhost,1433",
                            name="server",
                            default_value=BaseState.server,
                            width="100%",
                        ),
                        direction="column",
                        spacing="1",
                        width="100%",
                    ),
                    rx.flex(
                        rx.text("Database:", size="2", weight="bold"),
                        rx.input(
                            placeholder="OFM",
                            name="database",
                            default_value=BaseState.database,
                            width="100%",
                        ),
                        direction="column",
                        spacing="1",
                        width="100%",
                    ),
                    rx.flex(
                        rx.text("Username:", size="2", weight="bold"),
                        rx.input(
                            placeholder="SA",
                            name="username",
                            default_value=BaseState.username,
                            width="100%",
                        ),
                        direction="column",
                        spacing="1",
                        width="100%",
                    ),
                    rx.flex(
                        rx.text("Password:", size="2", weight="bold"),
                        rx.input(
                            placeholder="Password",
                            name="password",
                            type="password",
                            default_value=BaseState.password,
                            width="100%",
                        ),
                        direction="column",
                        spacing="1",
                        width="100%",
                    ),
                    rx.flex(
                        rx.dialog.close(
                            rx.button("Cancel", variant="soft", color_scheme="gray"),
                        ),
                        rx.dialog.close(
                            rx.button("Save", type="submit"),
                        ),
                        spacing="3",
                        justify="end",
                        width="100%",
                    ),
                    spacing="3",
                    width="100%",
                ),
                on_submit=BaseState.update_connection_params,
                reset_on_submit=False,
            ),
            max_width="450px",
        ),
    )


def filter_controls() -> rx.Component:
    """Filter controls for Master table."""
    return rx.hstack(
        rx.input(
            rx.input.slot(rx.icon("search")),
            placeholder="Search by ID or Well name...",
            size="2",
            width="250px",
            on_change=BaseState.filter_master_data,
        ),
        rx.select(
            BaseState.platform_filter_options,
            placeholder="Filter by Platform",
            size="2",
            width="180px",
            on_change=BaseState.filter_by_platform,
        ),
        rx.button(
            rx.icon("x", size=16),
            "Clear Filters",
            variant="soft",
            size="2",
            on_click=BaseState.clear_filters,
        ),
        spacing="2",
        align="center",
    )


def show_master_row(well: dict) -> rx.Component:
    """Display a Master table row."""
    return rx.table.row(
        rx.table.cell(
            rx.text(well["UniqueId"], size="2", weight="medium"),
        ),
        rx.table.cell(
            rx.text(well.get("Wellname", "-"), size="2"),
        ),
        rx.table.cell(
            rx.badge(well.get("Platform", "-"), size="1", color_scheme="blue"),
        ),
        rx.table.cell(
            rx.text(f"{well.get('X_top', 0):.2f}", size="2"),
        ),
        rx.table.cell(
            rx.text(f"{well.get('Y_top', 0):.2f}", size="2"),
        ),
        rx.table.cell(
            rx.text(f"{well.get('X_bot', 0):.2f}", size="2"),
        ),
        rx.table.cell(
            rx.text(f"{well.get('Y_bot', 0):.2f}", size="2"),
        ),
        style={"_hover": {"bg": rx.color("gray", 3)}},
        align="center",
    )


def master_table() -> rx.Component:
    """Main Master table component."""
    return rx.box(
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell(
                        rx.text("Unique ID", size="2", weight="bold")
                    ),
                    rx.table.column_header_cell(
                        rx.text("Well Name", size="2", weight="bold")
                    ),
                    rx.table.column_header_cell(
                        rx.text("Platform", size="2", weight="bold")
                    ),
                    rx.table.column_header_cell(
                        rx.text("X Top", size="2", weight="bold")
                    ),
                    rx.table.column_header_cell(
                        rx.text("Y Top", size="2", weight="bold")
                    ),
                    rx.table.column_header_cell(
                        rx.text("X Bottom", size="2", weight="bold")
                    ),
                    rx.table.column_header_cell(
                        rx.text("Y Bottom", size="2", weight="bold")
                    ),
                ),
            ),
            rx.table.body(
                rx.foreach(BaseState.master_data, show_master_row),
            ),
            variant="surface",
            size="2",
            width="100%",
        ),
        overflow_x="auto",
        overflow_y="auto",
        max_height="500px",
        width="100%",
    )


def connection_status_badge() -> rx.Component:
    """Display current database connection status."""
    return rx.badge(
        rx.icon("database", size=14),
        BaseState.connection_status,
        color_scheme=BaseState.connection_indicator_color,
        size="2",
    )


def stats_summary() -> rx.Component:
    """Summary statistics cards."""
    return rx.grid(
        rx.card(
            rx.vstack(
                rx.hstack(
                    rx.icon("layers", size=20, color=rx.color("blue", 9)),
                    rx.text("Total Wells", size="2", weight="bold"),
                    spacing="2",
                ),
                rx.heading(BaseState.total_wells, size="6"),
                spacing="2",
                align="start",
            ),
            padding="1.5em",
        ),
        rx.card(
            rx.vstack(
                rx.hstack(
                    rx.icon("building", size=20, color=rx.color("green", 9)),
                    rx.text("Platforms", size="2", weight="bold"),
                    spacing="2",
                ),
                rx.heading(BaseState.unique_platforms, size="6"),
                spacing="2",
                align="start",
            ),
            padding="1.5em",
        ),
        rx.card(
            rx.vstack(
                rx.hstack(
                    rx.icon("activity", size=20, color=rx.color("orange", 9)),
                    rx.text("Connection", size="2", weight="bold"),
                    spacing="2",
                ),
                connection_status_badge(),
                spacing="2",
                align="start",
            ),
            padding="1.5em",
        ),
        columns="3",
        spacing="4",
        width="100%",
    )