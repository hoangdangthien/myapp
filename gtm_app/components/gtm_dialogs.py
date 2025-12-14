"""Dialog components for GTM CRUD operations."""
import reflex as rx
from ..models import (
    Intervention, 
    FIELD_OPTIONS, 
    PLATFORM_OPTIONS, 
    RESERVOIR_OPTIONS,
    GTM_TYPE_OPTIONS,
    STATUS_OPTIONS
)
from ..states.gtm_state import GTMState
from .form_fields import form_field, select_field

def search_gtm():
    return rx.flex(
                    rx.input(
                        rx.input.slot(rx.icon("search")),
                        placeholder="Search intervention...",
                        size="2",
                        width="100%",
                        max_width="225px",
                        variant="surface",
                        on_change=lambda value:GTMState.filter_intervention(value)
                        
                    ),
                    )
def add_gtm_button() -> rx.Component:
    """Button and dialog for adding a new GTM/Intervention."""
    return rx.dialog.root(
        rx.dialog.trigger(
            rx.button(
                rx.icon("plus", size=16),
                rx.text("Add Intervention", size="2"),
                size="2",
            ),
        ),
        rx.dialog.content(
            rx.dialog.title("Add New Well Intervention"),
            rx.dialog.description("Fill the form with intervention details"),
            rx.form(
                rx.flex(
                    rx.grid(
                        form_field("UniqueId", "Enter unique ID", "text", "UniqueId"),
                        select_field("Field", FIELD_OPTIONS, "Field"),
                        select_field("Platform", PLATFORM_OPTIONS, "Platform"),
                        select_field("Reservoir", RESERVOIR_OPTIONS, "Reservoir"),
                        columns="2",
                        spacing="3",
                        width="100%",
                    ),
                    rx.grid(
                        select_field("Type GTM", GTM_TYPE_OPTIONS, "TypeGTM"),
                        form_field("Planning Date", "", "date", "PlanningDate"),
                        select_field("Status", STATUS_OPTIONS, "Status"),
                        columns="3",
                        spacing="3",
                        width="100%",
                    ),
                    rx.text("Decline Curve Parameters - Oil", size="2", weight="bold"),
                    rx.grid(
                        form_field("Initial Oil Rate", "0", "number", "InitialORate"),
                        form_field("b (oil)", "0", "number", "bo"),
                        form_field("Di (oil)", "0", "number", "Dio"),
                        columns="3",
                        spacing="2",
                        width="100%",
                    ),
                    rx.text("Decline Curve Parameters - Liquid", size="2", weight="bold"),
                    rx.grid(
                        form_field("Initial Liq Rate", "0", "number", "InitialLRate"),
                        form_field("b (liquid)", "0", "number", "bl"),
                        form_field("Di (liquid)", "0", "number", "Dil"),
                        columns="3",
                        spacing="2",
                        width="100%",
                    ),
                    rx.flex(
                        rx.dialog.close(
                            rx.button("Cancel", variant="soft", color_scheme="gray"),
                        ),
                        rx.dialog.close(
                            rx.button("Submit", type="submit"),
                        ),
                        spacing="3",
                        justify="end",
                    ),
                    direction="column",
                    spacing="3",
                ),
                on_submit=GTMState.add_gtm,
                reset_on_submit=True,
            ),
            max_width="650px",
        ),
    )


def load_excel_button() -> rx.Component:
    """Button and dialog for loading interventions from Excel."""
    return rx.dialog.root(
        rx.dialog.trigger(
            rx.button(
                rx.icon("file-spreadsheet", size=16),
                rx.text("Load Excel", size="2"),
                variant="soft",
                size="2",
            ),
        ),
        rx.dialog.content(
            rx.dialog.title("Load Interventions from Excel"),
            rx.dialog.description(
                "Upload an Excel file with intervention data. Required columns: "
                "UniqueId, Field, Platform, Reservoir, TypeGTM, PlanningDate, Status, "
                "InitialORate, bo, Dio, InitialLRate, bl, Dil"
            ),
            rx.vstack(
                rx.upload(
                    rx.vstack(
                        rx.icon("upload", size=32, color=rx.color("gray", 9)),
                        rx.text("Drop Excel file here or click to browse"),
                        rx.text("(.xlsx, .xls)", size="1", color=rx.color("gray", 10)),
                        align="center",
                        spacing="2",
                    ),
                    id="excel_upload",
                    accept={".xlsx": ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"],
                            ".xls": ["application/vnd.ms-excel"]},
                    max_files=1,
                    border=f"2px dashed {rx.color('gray', 6)}",
                    padding="2em",
                    border_radius="8px",
                    width="100%",
                ),
                rx.flex(
                    rx.dialog.close(
                        rx.button("Cancel", variant="soft", color_scheme="gray"),
                    ),
                    rx.button(
                        "Upload",
                        on_click=GTMState.handle_excel_upload(rx.upload_files(upload_id="excel_upload")),
                    ),
                    spacing="3",
                    justify="end",
                    width="100%",
                ),
                spacing="4",
                width="100%",
            ),
            max_width="500px",
        ),
    )


def update_gtm_dialog(gtm: Intervention) -> rx.Component:
    """Dialog for editing an existing GTM/Intervention."""
    return rx.dialog.root(
        rx.dialog.trigger(
            rx.button(
                rx.icon("pencil", size=14),
                variant="ghost",
                color_scheme="blue",
                size="1",
                on_click=lambda: GTMState.get_gtm(gtm),
            ),
        ),
        rx.dialog.content(
            rx.dialog.title("Edit Well Intervention"),
            rx.dialog.description("Update the intervention details"),
            rx.form(
                rx.flex(
                    rx.text(f"UniqueId: {gtm.UniqueId}", weight="bold", size="3"),
                    rx.grid(
                        select_field("Field", FIELD_OPTIONS, "Field", gtm.Field),
                        select_field("Platform", PLATFORM_OPTIONS, "Platform", gtm.Platform),
                        select_field("Reservoir", RESERVOIR_OPTIONS, "Reservoir", gtm.Reservoir),
                        columns="3",
                        spacing="2",
                        width="100%",
                    ),
                    rx.grid(
                        select_field("Type GTM", GTM_TYPE_OPTIONS, "TypeGTM", gtm.TypeGTM),
                        form_field("Planning Date", "", "date", "PlanningDate", gtm.PlanningDate),
                        select_field("Status", STATUS_OPTIONS, "Status", gtm.Status),
                        columns="3",
                        spacing="2",
                        width="100%",
                    ),
                    rx.text("Decline Parameters - Oil", size="2", weight="bold"),
                    rx.grid(
                        form_field("Initial Oil Rate", "", "number", "InitialORate", gtm.InitialORate.to(str)),
                        form_field("b (oil)", "", "number", "bo", gtm.bo.to(str)),
                        form_field("Di (oil)", "", "number", "Dio", gtm.Dio.to(str)),
                        columns="3",
                        spacing="2",
                        width="100%",
                    ),
                    rx.text("Decline Parameters - Liquid", size="2", weight="bold"),
                    rx.grid(
                        form_field("Initial Liq Rate", "0", "number", "InitialLRate", gtm.InitialLRate.to(str)),#use to str is working not use str(gtm.InitialLRate)
                        form_field("b (liquid)", "0", "number", "bl", gtm.bl.to(str)),
                        form_field("Di (liquid)", "0", "number", "Dil", gtm.Dil.to(str)),
                        columns="3",
                        spacing="2",
                        width="100%",
                    ),
                    rx.flex(
                        rx.dialog.close(
                            rx.button("Cancel", variant="soft", color_scheme="gray"),
                        ),
                        rx.dialog.close(
                            rx.button("Update", type="submit"),
                        ),
                        spacing="3",
                        justify="end",
                    ),
                    direction="column",
                    spacing="3",
                ),
                on_submit=GTMState.update_gtm,
                reset_on_submit=False,
            ),
            max_width="650px",
        ),
    )


def delete_gtm_dialog(gtm: Intervention) -> rx.Component:
    """Dialog for confirming GTM deletion."""
    return rx.alert_dialog.root(
        rx.alert_dialog.trigger(
            rx.button(
                rx.icon("trash-2", size=14),
                variant="ghost",
                color_scheme="red",
                size="1",
            ),
        ),
        rx.alert_dialog.content(
            rx.alert_dialog.title("Delete Well Intervention"),
            rx.alert_dialog.description(
                f"Are you sure you want to delete '{gtm.UniqueId}'? This cannot be undone.",
            ),
            rx.flex(
                rx.alert_dialog.cancel(
                    rx.button("Cancel", variant="soft", color_scheme="gray"),
                ),
                rx.alert_dialog.action(
                    rx.button(
                        "Delete",
                        color_scheme="red",
                        on_click=lambda: GTMState.delete_gtm(gtm.UniqueId),
                    ),
                ),
                spacing="3",
                justify="end",
            ),
        ),
    )
