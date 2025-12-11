"""Dialog components for GTM CRUD operations."""
import reflex as rx
from ..models import (
    Intervention, 
    FIELD_OPTIONS, 
    PLATFORM_OPTIONS, 
    RESERVOIR_OPTIONS,
    GTM_TYPE_OPTIONS
)
from ..states.gtm_state import GTMState
from .form_fields import form_field, select_field


def add_gtm_button() -> rx.Component:
    """Button and dialog for adding a new GTM/Intervention."""
    return rx.dialog.root(
        rx.dialog.trigger(
            rx.button(
                rx.icon("plus", size=20),
                rx.text("Add Well Intervention", size="3"),
                size="3",
            ),
        ),
        rx.dialog.content(
            rx.dialog.title("Add New Well Intervention"),
            rx.dialog.description(
                "Fill the form with the intervention details"
            ),
            rx.form(
                rx.flex(
                    form_field("UniqueId", "Enter unique identifier", "text", "UniqueId"),
                    select_field("Field", FIELD_OPTIONS, "Field"),
                    select_field("Platform", PLATFORM_OPTIONS, "Platform"),
                    select_field("Reservoir", RESERVOIR_OPTIONS, "Reservoir"),
                    select_field("Type GTM", GTM_TYPE_OPTIONS, "TypeGTM"),
                    form_field("Planning Date", "Select date", "date", "PlanningDate"),
                    form_field("Status", "Plan", "text", "Status", required=False),
                    rx.text("Decline Curve Parameters - Oil", size="2", weight="bold", margin_top="0.5em"),
                    rx.grid(
                        form_field("Initial Oil Rate (bbl/d)", "0", "number", "InitialORate"),
                        form_field("b (oil)", "0", "number", "bo"),
                        form_field("Di (oil)", "0", "number", "Dio"),
                        columns="3",
                        spacing="2",
                        width="100%",
                    ),
                    rx.text("Decline Curve Parameters - Liquid", size="2", weight="bold", margin_top="0.5em"),
                    rx.grid(
                        form_field("Initial Liquid Rate (bbl/d)", "0", "number", "InitialLRate"),
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
                        margin_top="1em",
                    ),
                    direction="column",
                    spacing="2",
                ),
                on_submit=GTMState.add_gtm,
                reset_on_submit=True,
            ),
            max_width="600px",
        ),
    )


def update_gtm_dialog(gtm: Intervention) -> rx.Component:
    """Dialog for editing an existing GTM/Intervention.
    
    Args:
        gtm: The intervention record to edit
    """
    return rx.dialog.root(
        rx.dialog.trigger(
            rx.button(
                rx.icon("pencil", size=16),
                variant="soft",
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
                    select_field("Field", FIELD_OPTIONS, "Field", gtm.Field),
                    select_field("Platform", PLATFORM_OPTIONS, "Platform", gtm.Platform),
                    select_field("Reservoir", RESERVOIR_OPTIONS, "Reservoir", gtm.Reservoir),
                    select_field("Type GTM", GTM_TYPE_OPTIONS, "TypeGTM", gtm.TypeGTM),
                    form_field("Planning Date", "Date", "date", "PlanningDate", gtm.PlanningDate),
                    form_field("Status", "Status", "text", "Status", gtm.Status, required=False),
                    rx.text("Decline Curve Parameters - Oil", size="2", weight="bold", margin_top="0.5em"),
                    rx.grid(
                        form_field("Initial Oil Rate", "0", "number", "InitialORate", str(gtm.InitialORate)),
                        form_field("b (oil)", "0", "number", "bo", str(gtm.bo)),
                        form_field("Di (oil)", "0", "number", "Dio", str(gtm.Dio)),
                        columns="3",
                        spacing="2",
                        width="100%",
                    ),
                    rx.text("Decline Curve Parameters - Liquid", size="2", weight="bold", margin_top="0.5em"),
                    rx.grid(
                        form_field("Initial Liquid Rate", "0", "number", "InitialLRate", str(gtm.InitialLRate)),
                        form_field("b (liquid)", "0", "number", "bl", str(gtm.bl)),
                        form_field("Di (liquid)", "0", "number", "Dil", str(gtm.Dil)),
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
                        margin_top="1em",
                    ),
                    direction="column",
                    spacing="2",
                ),
                on_submit=GTMState.update_gtm,
                reset_on_submit=False,
            ),
            max_width="600px",
        ),
    )


def delete_gtm_dialog(gtm: Intervention) -> rx.Component:
    """Dialog for confirming GTM deletion.
    
    Args:
        gtm: The intervention record to delete
    """
    return rx.alert_dialog.root(
        rx.alert_dialog.trigger(
            rx.button(
                rx.icon("trash-2", size=16),
                variant="soft",
                color_scheme="red",
                size="1",
            ),
        ),
        rx.alert_dialog.content(
            rx.alert_dialog.title("Delete Well Intervention"),
            rx.alert_dialog.description(
                f"Are you sure you want to delete intervention '{gtm.UniqueId}'? "
                "This action cannot be undone.",
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
