"""Updated table components with pagination.

Contains updated completion_table() and intervention_table() functions
that include pagination controls.

INSTRUCTIONS:
1. Import pagination_controls from components.pagination
2. Replace existing table functions with these versions
"""

import reflex as rx
from ..models import CompletionID, InterventionID
from ..states.production_state import ProductionState
from ..states.gtm_state import GTMState
from .pagination import pagination_controls, simple_pagination_controls
from .dialogs import update_completion_dialog, update_intervention_dialog, delete_intervention_dialog


# ============================================================
# COMPLETION TABLE WITH PAGINATION
# ============================================================

def completion_table_header() -> rx.Component:
    """Header for CompletionID table."""
    return rx.table.header(
        rx.table.row(
            rx.table.column_header_cell(rx.text("UniqueId", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Well", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Reservoir", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("KH", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Do", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Dl", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Dip", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Dir", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Actions", size="1", weight="bold")),
        ),
    )


def show_completion_row(completion: CompletionID) -> rx.Component:
    """Display a completion in a table row with Dip and Dir columns."""
    return rx.table.row(
        rx.table.cell(rx.text(completion.UniqueId, size="1", weight="medium")),
        rx.table.cell(rx.text(rx.cond(completion.WellName, completion.WellName, "-"), size="1")),
        rx.table.cell(rx.badge(rx.cond(completion.Reservoir, completion.Reservoir, "-"), color_scheme="blue", size="1")),
        rx.table.cell(rx.text(rx.cond(completion.KH, completion.KH.to(str), "-"), size="1")),
        rx.table.cell(rx.badge(rx.cond(completion.Do, completion.Do.to(str), "-"), color_scheme="green", size="1")),
        rx.table.cell(rx.badge(rx.cond(completion.Dl, completion.Dl.to(str), "-"), color_scheme="green", size="1")),
        rx.table.cell(rx.badge(rx.cond(completion.Dip, completion.Dip.to(str), "0"), color_scheme="orange", size="1")),
        rx.table.cell(rx.badge(rx.cond(completion.Dir, completion.Dir.to(str), "0"), color_scheme="purple", size="1")),
        rx.table.cell(update_completion_dialog(completion)),
        style={"_hover": {"bg": rx.color("gray", 3)}, "cursor": "pointer"},
        align="center",
        on_click=lambda: ProductionState.set_selected_id(completion.UniqueId),
    )


def completion_table_with_pagination() -> rx.Component:
    """Main CompletionID table component with pagination.
    
    REPLACES: completion_table() in components/tables.py or production_components.py
    """
    return rx.vstack(
        # Table with scrollable container
        rx.box(
            rx.table.root(
                completion_table_header(),
                rx.table.body(
                    rx.foreach(
                        ProductionState.paginated_completions,  # Use paginated data
                        show_completion_row
                    ),
                ),
                variant="surface",
                size="1",
                width="100%",
            ),
            overflow_y="auto",
            overflow_x="auto",
            max_height="350px",
            width="100%",
        ),
        # Pagination controls
        rx.divider(),
        pagination_controls(
            current_page=ProductionState.completion_current_page,
            total_pages=ProductionState.completion_total_pages,
            page_size=ProductionState.completion_page_size,
            total_count=ProductionState.completion_total_count,
            on_prev=ProductionState.completion_prev_page,
            on_next=ProductionState.completion_next_page,
            on_page_size_change=ProductionState.set_completion_page_size,
            page_size_options=[10, 20, 50, 100],
        ),
        width="100%",
        spacing="2",
    )


# ============================================================
# INTERVENTION TABLE WITH PAGINATION
# ============================================================

def intervention_table_header() -> rx.Component:
    """Header for InterventionID table."""
    return rx.table.header(
        rx.table.row(
            rx.table.column_header_cell(rx.text("UniqueId", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Field", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Platform", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Reservoir", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Type", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Date", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Status", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("ORate", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("bo", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Dio", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("LRate", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("bl", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Dil", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Actions", size="1", weight="bold")),
        ),
    )


def show_intervention_row(intervention: InterventionID) -> rx.Component:
    """Show an intervention in a table row with edit/delete buttons."""
    return rx.table.row(
        rx.table.cell(rx.text(intervention.UniqueId, size="1", weight="medium")),
        rx.table.cell(rx.text(intervention.Field, size="1")),
        rx.table.cell(rx.text(intervention.Platform, size="1")),
        rx.table.cell(rx.text(intervention.Reservoir, size="1")),
        rx.table.cell(rx.badge(intervention.TypeGTM, color_scheme="blue", size="1")),
        rx.table.cell(rx.text(intervention.PlanningDate, size="1")),
        rx.table.cell(
            rx.badge(
                intervention.Status,
                color_scheme=rx.cond(
                    intervention.Status == "Done", 
                    "green", 
                    rx.cond(intervention.Status == "Plan", "yellow", "gray")
                ),
                size="1"
            )
        ),
        rx.table.cell(rx.text(f"{intervention.InitialORate:.0f}", size="1")),
        rx.table.cell(rx.text(f"{intervention.bo:.2f}", size="1")),
        rx.table.cell(rx.text(f"{intervention.Dio:.3f}", size="1")),
        rx.table.cell(rx.text(f"{intervention.InitialLRate:.0f}", size="1")),
        rx.table.cell(rx.text(f"{intervention.bl:.2f}", size="1")),
        rx.table.cell(rx.text(f"{intervention.Dil:.3f}", size="1")),
        rx.table.cell(
            rx.hstack(
                update_intervention_dialog(intervention), 
                delete_intervention_dialog(intervention), 
                spacing="1"
            )
        ),
        style={"_hover": {"bg": rx.color("gray", 3)}},
        align="center",
    )


def intervention_table_with_pagination() -> rx.Component:
    """Main InterventionID table component with pagination.
    
    REPLACES: intervention_table() in components/tables.py
    """
    return rx.vstack(
        # Table with scrollable container
        rx.box(
            rx.table.root(
                intervention_table_header(),
                rx.table.body(
                    rx.foreach(
                        GTMState.paginated_interventions,  # Use paginated data
                        show_intervention_row
                    ),
                ),
                variant="surface",
                size="1",
                width="100%",
            ),
            overflow_y="auto",
            overflow_x="auto",
            max_height="350px",
            width="100%",
        ),
        # Pagination controls
        rx.divider(),
        pagination_controls(
            current_page=GTMState.intervention_current_page,
            total_pages=GTMState.intervention_total_pages,
            page_size=GTMState.intervention_page_size,
            total_count=GTMState.intervention_total_count,
            on_prev=GTMState.intervention_prev_page,
            on_next=GTMState.intervention_next_page,
            on_page_size_change=GTMState.set_intervention_page_size,
            page_size_options=[10, 20, 50, 100],
        ),
        width="100%",
        spacing="2",
    )


# ============================================================
# COMPACT PAGINATION VARIANTS (Alternative simpler versions)
# ============================================================

def completion_table_simple_pagination() -> rx.Component:
    """CompletionID table with simple pagination (just prev/next).
    
    Use this for a more compact UI.
    """
    return rx.vstack(
        rx.box(
            rx.table.root(
                completion_table_header(),
                rx.table.body(
                    rx.foreach(
                        ProductionState.paginated_completions,
                        show_completion_row
                    ),
                ),
                variant="surface",
                size="1",
                width="100%",
            ),
            overflow_y="auto",
            overflow_x="auto",
            max_height="350px",
            width="100%",
        ),
        rx.hstack(
            rx.text(
                f"Showing {ProductionState.completion_start_item} - {ProductionState.completion_end_item} of {ProductionState.completion_total_count}",
                size="1",
                color=rx.color("gray", 11),
            ),
            rx.spacer(),
            simple_pagination_controls(
                current_page=ProductionState.completion_current_page,
                total_pages=ProductionState.completion_total_pages,
                on_prev=ProductionState.completion_prev_page,
                on_next=ProductionState.completion_next_page,
            ),
            width="100%",
            align="center",
            padding_y="0.5em",
        ),
        width="100%",
        spacing="2",
    )


def intervention_table_simple_pagination() -> rx.Component:
    """InterventionID table with simple pagination (just prev/next).
    
    Use this for a more compact UI.
    """
    return rx.vstack(
        rx.box(
            rx.table.root(
                intervention_table_header(),
                rx.table.body(
                    rx.foreach(
                        GTMState.paginated_interventions,
                        show_intervention_row
                    ),
                ),
                variant="surface",
                size="1",
                width="100%",
            ),
            overflow_y="auto",
            overflow_x="auto",
            max_height="350px",
            width="100%",
        ),
        rx.hstack(
            rx.text(
                f"Showing {GTMState.intervention_start_item} - {GTMState.intervention_end_item} of {GTMState.intervention_total_count}",
                size="1",
                color=rx.color("gray", 11),
            ),
            rx.spacer(),
            simple_pagination_controls(
                current_page=GTMState.intervention_current_page,
                total_pages=GTMState.intervention_total_pages,
                on_prev=GTMState.intervention_prev_page,
                on_next=GTMState.intervention_next_page,
            ),
            width="100%",
            align="center",
            padding_y="0.5em",
        ),
        width="100%",
        spacing="2",
    )