"""Table component for displaying GTM/Intervention data."""
import reflex as rx
from ..models import Intervention
from ..states.gtm_state import GTMState
from .gtm_dialogs import update_gtm_dialog, delete_gtm_dialog


def show_intervention(gtm: Intervention) -> rx.Component:
    """Show an intervention in a table row with edit/delete buttons.
    
    Args:
        gtm: The intervention record to display
    """
    return rx.table.row(
        rx.table.cell(gtm.UniqueId),
        rx.table.cell(gtm.Field),
        rx.table.cell(gtm.Platform),
        rx.table.cell(gtm.Reservoir),
        rx.table.cell(
            rx.badge(gtm.TypeGTM, color_scheme="blue")
        ),
        rx.table.cell(gtm.PlanningDate),
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
                )
            )
        ),
        rx.table.cell(f"{gtm.InitialORate:.1f}"),
        rx.table.cell(f"{gtm.InitialLRate:.1f}"),
        rx.table.cell(
            rx.hstack(
                update_gtm_dialog(gtm),
                delete_gtm_dialog(gtm),
                spacing="2",
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
                    rx.table.column_header_cell("UniqueId"),
                    rx.table.column_header_cell("Field"),
                    rx.table.column_header_cell("Platform"),
                    rx.table.column_header_cell("Reservoir"),
                    rx.table.column_header_cell("Type GTM"),
                    rx.table.column_header_cell("Planning Date"),
                    rx.table.column_header_cell("Status"),
                    rx.table.column_header_cell("Oil Rate (bbl/d)"),
                    rx.table.column_header_cell("Liquid Rate (bbl/d)"),
                    rx.table.column_header_cell("Actions"),
                ),
            ),
            rx.table.body(
                rx.foreach(GTMState.GTM, show_intervention),
            ),
            variant="surface",
            size="2",
            width="100%",
        ),
        overflow_x="auto",
        width="100%",
    )
