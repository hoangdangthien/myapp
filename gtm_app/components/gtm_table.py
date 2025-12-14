"""Table component for displaying GTM/Intervention data."""
import reflex as rx
from ..models import Intervention
from ..states.gtm_state import GTMState
from .gtm_dialogs import update_gtm_dialog, delete_gtm_dialog


def show_intervention(gtm: Intervention) -> rx.Component:
    """Show an intervention in a table row with edit/delete buttons."""
    return rx.table.row(
        rx.table.cell(
            rx.text(gtm.UniqueId, size="1", weight="medium"),
        ),
        rx.table.cell(rx.text(gtm.Field, size="1")),
        rx.table.cell(rx.text(gtm.Platform, size="1")),
        rx.table.cell(rx.text(gtm.Reservoir, size="1")),
        rx.table.cell(
            rx.badge(gtm.TypeGTM, color_scheme="blue", size="1")
        ),
        rx.table.cell(rx.text(gtm.PlanningDate, size="1")),
        rx.table.cell(
            rx.badge(
                gtm.Status,
                color_scheme=rx.cond(
                    gtm.Status == "Completed",
                    "green",
                    rx.cond(
                        gtm.Status == "In Progress",
                        "yellow",
                        "gray"
                    )
                ),
                size="1"
            )
        ),
        rx.table.cell(rx.text(f"{gtm.InitialORate:.0f}", size="1")),
        rx.table.cell(rx.text(f"{gtm.bo:.2f}", size="1")),
        rx.table.cell(rx.text(f"{gtm.Dio:.3f}", size="1")),
        rx.table.cell(rx.text(f"{gtm.InitialLRate:.0f}", size="1")),
        rx.table.cell(rx.text(f"{gtm.bl:.2f}", size="1")),
        rx.table.cell(rx.text(f"{gtm.Dil:.3f}", size="1")),
        rx.table.cell(
            rx.hstack(
                update_gtm_dialog(gtm),
                delete_gtm_dialog(gtm),
                spacing="1",
            ),
        ),
        style={"_hover": {"bg": rx.color("gray", 3)}},
        align="center",
    )


def gtm_table() -> rx.Component:
    """Create the main data table for interventions."""
    return rx.box(
        
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell(rx.text("ID", size="1", weight="bold")),
                    rx.table.column_header_cell(rx.text("Field", size="1", weight="bold")),
                    rx.table.column_header_cell(rx.text("Platform", size="1", weight="bold")),
                    rx.table.column_header_cell(rx.text("Reservoir", size="1", weight="bold")),
                    rx.table.column_header_cell(rx.text("Type", size="1", weight="bold")),
                    rx.table.column_header_cell(rx.text("Date", size="1", weight="bold")),
                    rx.table.column_header_cell(rx.text("Status", size="1", weight="bold")),
                    rx.table.column_header_cell(rx.text("qi_o", size="1", weight="bold")),
                    rx.table.column_header_cell(rx.text("b_o", size="1", weight="bold")),
                    rx.table.column_header_cell(rx.text("Di_o", size="1", weight="bold")),
                    rx.table.column_header_cell(rx.text("qi_l", size="1", weight="bold")),
                    rx.table.column_header_cell(rx.text("b_l", size="1", weight="bold")),
                    rx.table.column_header_cell(rx.text("Di_l", size="1", weight="bold")),
                    rx.table.column_header_cell(rx.text("Actions", size="1", weight="bold")),
                ),
            ),
            rx.table.body(
                rx.foreach(GTMState.GTM, show_intervention),
            ),
            variant="surface",
            size="1",
            width="100%",
        ),
        overflow_x="auto",
        width="100%",
        max_height="350px",
        overflow_y="auto",
    )


def production_record_table() -> rx.Component:
    """Table showing production records for selected intervention."""
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
                    GTMState.production_table_data,
                    lambda row: rx.table.row(
                        rx.table.cell(rx.text(row["Date"], size="1")),
                        rx.table.cell(rx.text(row["OilRate"], size="1")),
                        rx.table.cell(rx.text(row["LiqRate"], size="1")),
                        rx.table.cell(rx.text(row["WC"], size="1")),
                    )
                ),
            ),
            variant="surface",
            size="1",
            width="100%",
        ),
        overflow_y="auto",
        max_height="200px",
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
                ),
            ),
            rx.table.body(
                rx.foreach(
                    GTMState.forecast_table_data,
                    lambda row: rx.table.row(
                        rx.table.cell(rx.text(row["Date"], size="1")),
                        rx.table.cell(rx.text(row["OilRate"], size="1")),
                        rx.table.cell(rx.text(row["LiqRate"], size="1")),
                    )
                ),
            ),
            variant="surface",
            size="1",
            width="100%",
        ),
        overflow_y="auto",
        max_height="200px",
        width="100%",
    )
