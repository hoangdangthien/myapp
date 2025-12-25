import reflex as rx
from ..states.production_state import ProductionState
from ..states.gtm_state import GTMState
from ..models import *
from .form_fields import *

def validation_info_callout() -> rx.Component:
    """Display validation rules for the form."""
    return rx.callout(
        rx.vstack(
            rx.text("Input Validation Rules:", weight="bold", size="1"),
            rx.text("• Rates: 0 - 10,000 (oil) / 20,000 (liquid) t/day", size="1"),
            rx.text("• b parameter: 0 - 2 (0=exponential, 1=harmonic)", size="1"),
            rx.text("• Di rate: 0 - 1 (1/month)", size="1"),
            spacing="0",
            align="start",
        ),
        icon="info",
        color_scheme="blue",
        size="1",
    )
#Add Intervention dialogs
def add_intervention_button() -> rx.Component:
    """Button and dialog for adding a new Intervention with validated inputs."""
    return rx.dialog.root(
        rx.dialog.trigger(
            rx.button(
                rx.icon("plus", size=14),
                rx.text("Add Intervention", size="2"),
                size="1",
            ),
        ),
        rx.dialog.content(
            rx.dialog.title("Add New Well Intervention"),
            rx.dialog.description("Fill the form with intervention details. Fields marked with * are required."),
            rx.form(
                rx.flex(
                    # Basic Info Section
                    rx.grid(
                        form_field("UniqueId *", "Enter unique ID", "text", "UniqueId"),
                        select_field("Field", FIELD_OPTIONS, "Field"),
                        select_field("Platform", PLATFORM_OPTIONS, "Platform"),
                        select_field("Reservoir", RESERVOIR_OPTIONS, "Reservoir"),
                        columns="2",
                        spacing="3",
                        width="100%",
                    ),
                    
                    # Type and Status Section
                    rx.grid(
                        select_field("Type GTM", GTM_TYPE_OPTIONS, "TypeGTM"),
                        select_field("Category", GTM_CATEGORY_OPTIONS, "Category"),
                        form_field("Planning Date *", "", "date", "PlanningDate"),
                        select_field("Status", STATUS_OPTIONS, "Status"),
                        columns="2",
                        spacing="3",
                        width="100%",
                    ),
                    
                    # Oil Decline Parameters with Validation
                    rx.hstack(
                        rx.text("Decline Curve Parameters - Oil", size="2", weight="bold"),
                        rx.badge("Validated", color_scheme="green", size="1"),
                        spacing="2",
                        align="center",
                    ),
                    rx.grid(
                        validated_number_field(
                            label="Initial Oil Rate",
                            name="InitialORate",
                            default_value="0",
                            min_value=0,
                            max_value=10000,
                            step="0.1",
                            helper_text="t/day",
                        ),
                        validated_number_field(
                            label="b (oil)",
                            name="bo",
                            default_value="0",
                            min_value=0,
                            max_value=2,
                            step="0.01",
                            helper_text="Arps exponent",
                        ),
                        validated_number_field(
                            label="Di (oil)",
                            name="Dio",
                            default_value="0",
                            min_value=0,
                            max_value=1,
                            step="0.0001",
                            helper_text="1/month",
                        ),
                        columns="3",
                        spacing="2",
                        width="100%",
                    ),
                    
                    # Liquid Decline Parameters with Validation
                    rx.hstack(
                        rx.text("Decline Curve Parameters - Liquid", size="2", weight="bold"),
                        rx.badge("Validated", color_scheme="green", size="1"),
                        spacing="2",
                        align="center",
                    ),
                    rx.grid(
                        validated_number_field(
                            label="Initial Liq Rate",
                            name="InitialLRate",
                            default_value="0",
                            min_value=0,
                            max_value=20000,
                            step="0.1",
                            helper_text="t/day",
                        ),
                        validated_number_field(
                            label="b (liquid)",
                            name="bl",
                            default_value="0",
                            min_value=0,
                            max_value=2,
                            step="0.01",
                            helper_text="Arps exponent",
                        ),
                        validated_number_field(
                            label="Di (liquid)",
                            name="Dil",
                            default_value="0",
                            min_value=0,
                            max_value=1,
                            step="0.0001",
                            helper_text="1/month",
                        ),
                        columns="3",
                        spacing="2",
                        width="100%",
                    ),
                    
                    # Description
                    rx.text("Description", size="2", weight="bold"),
                    form_field(
                        "Describe intervention", 
                        "Describe detail intervention activity", 
                        "text", 
                        "Describe",
                        required=False
                    ),
                    
                    # Validation Info
                    validation_info_callout(),
                    
                    # Action Buttons
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
            max_width="700px",
        ),
    )
#Update Intervention dialogs
def update_intervention_dialog(Intv: InterventionID) -> rx.Component:
    """Dialog for editing an existing Intervention with validated inputs."""
    return rx.dialog.root(
        rx.dialog.trigger(
            rx.button(
                rx.icon("pencil", size=14),
                variant="ghost",
                color_scheme="blue",
                size="1",
                on_click=lambda: GTMState.get_gtm(Intv),
            ),
        ),
        rx.dialog.content(
            rx.dialog.title("Edit Well Intervention"),
            rx.dialog.description("Update the intervention details. Values must be within allowed ranges."),
            rx.form(
                rx.flex(
                    # UniqueId Display (not editable)
                    rx.hstack(
                        rx.text("UniqueId:", weight="bold", size="2"),
                        rx.badge(Intv.UniqueId, color_scheme="blue", size="2"),
                        spacing="2",
                        align="center",
                    ),
                    
                    # Basic Info
                    rx.grid(
                        select_field("Field", FIELD_OPTIONS, "Field", Intv.Field),
                        select_field("Platform", PLATFORM_OPTIONS, "Platform", Intv.Platform),
                        select_field("Reservoir", RESERVOIR_OPTIONS, "Reservoir", Intv.Reservoir),
                        columns="2",
                        spacing="2",
                        width="100%",
                    ),
                    
                    # Type and Status
                    rx.grid(
                        select_field("Type GTM", GTM_TYPE_OPTIONS, "TypeGTM", Intv.TypeGTM),
                        select_field("Category", GTM_CATEGORY_OPTIONS, "Category", Intv.Category),
                        form_field("Planning Date", "", "date", "PlanningDate", str(Intv.PlanningDate)),
                        select_field("Status", STATUS_OPTIONS, "Status", Intv.Status),
                        columns="2",
                        spacing="2",
                        width="100%",
                    ),
                    
                    # Oil Decline Parameters with Validation
                    rx.hstack(
                        rx.text("Decline Parameters - Oil", size="2", weight="bold"),
                        rx.badge("Range: see hints", color_scheme="gray", size="1"),
                        spacing="2",
                    ),
                    rx.grid(
                        validated_number_field(
                            label="Initial Oil Rate",
                            name="InitialORate",
                            default_value=Intv.InitialORate.to(str),
                            min_value=0,
                            max_value=10000,
                            step="0.1",
                            helper_text="t/day",
                        ),
                        validated_number_field(
                            label="b (oil)",
                            name="bo",
                            default_value=Intv.bo.to(str),
                            min_value=0,
                            max_value=2,
                            step="0.01",
                            helper_text="0-2",
                        ),
                        validated_number_field(
                            label="Di (oil)",
                            name="Dio",
                            default_value=Intv.Dio.to(str),
                            min_value=0,
                            max_value=1,
                            step="0.0001",
                            helper_text="1/month",
                        ),
                        columns="3",
                        spacing="2",
                        width="100%",
                    ),
                    
                    # Liquid Decline Parameters with Validation
                    rx.hstack(
                        rx.text("Decline Parameters - Liquid", size="2", weight="bold"),
                        rx.badge("Range: see hints", color_scheme="gray", size="1"),
                        spacing="2",
                    ),
                    rx.grid(
                        validated_number_field(
                            label="Initial Liq Rate",
                            name="InitialLRate",
                            default_value=Intv.InitialLRate.to(str),
                            min_value=0,
                            max_value=20000,
                            step="0.1",
                            helper_text="t/day",
                        ),
                        validated_number_field(
                            label="b (liquid)",
                            name="bl",
                            default_value=Intv.bl.to(str),
                            min_value=0,
                            max_value=2,
                            step="0.01",
                            helper_text="0-2",
                        ),
                        validated_number_field(
                            label="Di (liquid)",
                            name="Dil",
                            default_value=Intv.Dil.to(str),
                            min_value=0,
                            max_value=1,
                            step="0.0001",
                            helper_text="1/month",
                        ),
                        columns="3",
                        spacing="2",
                        width="100%",
                    ),
                    
                    # Description
                    rx.text("Description", size="2", weight="bold"),
                    form_field(
                        "Describe intervention", 
                        "Describe detail intervention activity", 
                        "text", 
                        "Describe", 
                        Intv.Describe.to(str),
                        required=False
                    ),
                    
                    # Action Buttons
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
            max_width="700px",
        ),
    )
#Delete Intervention
def delete_intervention_dialog(Intv: InterventionID) -> rx.Component:
    """Dialog for confirming Intervention deletion."""
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
                f"Are you sure you want to delete '{Intv.UniqueId}'? This cannot be undone.",
            ),
            rx.flex(
                rx.alert_dialog.cancel(
                    rx.button("Cancel", variant="soft", color_scheme="gray"),
                ),
                rx.alert_dialog.action(
                    rx.button(
                        "Delete",
                        color_scheme="red",
                        on_click=lambda: GTMState.delete_gtm(Intv.UniqueId),
                    ),
                ),
                spacing="3",
                justify="end",
            ),
        ),
    )
#Load Intervention Input
def load_intervention_button() -> rx.Component:
    """Button and dialog for loading Interventions from Excel."""
    return rx.dialog.root(
        rx.dialog.trigger(
            rx.button(
                rx.icon("file-spreadsheet", size=14),
                rx.text("Load File", size="2"),
                size="1",
            ),
        ),
        rx.dialog.content(
            rx.dialog.title("Load Interventions from Excel"),
            rx.dialog.description(
                "Upload an Excel file with intervention data. Required columns: "
                "UniqueId, Field, Platform, Reservoir, TypeGTM, Category, PlanningDate, Status, "
                "InitialORate, bo, Dio, InitialLRate, bl, Dil, Detail describe intervention activity"
            ),
            rx.vstack(
                rx.callout(
                    rx.vstack(
                        rx.text("Value Validation:", weight="bold", size="1"),
                        rx.text("• InitialORate: 0 - 10,000 t/day", size="1"),
                        rx.text("• InitialLRate: 0 - 20,000 t/day", size="1"),
                        rx.text("• bo, bl: 0 - 2", size="1"),
                        rx.text("• Dio, Dil: 0 - 1 (1/month)", size="1"),
                        spacing="0",
                        align="start",
                    ),
                    icon="alert-triangle",
                    color_scheme="yellow",
                    size="1",
                ),
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
#Search Intervention
def search_interventions():
    return rx.flex(
        rx.input(
            rx.input.slot(rx.icon("search")),
            placeholder="Search Intervention...",
            size="1",
            width="100%",
            max_width="225px",
            variant="surface",
            on_change=lambda value: GTMState.filter_intervention(value),
            debounce_timeout=300,
        ),
    )
#Search Completion 
def search_completions() -> rx.Component:
    """Filter controls for CompletionID table with reservoir filter."""
    return rx.flex(
        rx.input(
            rx.input.slot(rx.icon("search")),
            placeholder="Search by ID or Well name...",
            size="1",
            width="200px",
            on_change= lambda value : ProductionState.filter_completions(value),
            debounce_timeout=300,
        ),
    )
#Update Completion decline parameters
def update_completion_dialog(completion: CompletionID) -> rx.Component:
    """Dialog for editing CompletionID decline parameters (Do, Dl, Dip, Dir)."""
    return rx.dialog.root(
        rx.dialog.trigger(
            rx.button(
                rx.icon("pencil", size=14),
                variant="ghost",
                color_scheme="blue",
                size="1",
                on_click=lambda: ProductionState.get_completion(completion),
            ),
        ),
        rx.dialog.content(
            rx.dialog.title("Edit Decline Parameters"),
            rx.dialog.description(
                rx.hstack(
                    rx.vstack(
                        rx.text("UniqueId:", size="1", weight="bold"),
                        rx.text(completion.UniqueId, size="2"),
                        spacing="0",
                    ),
                    rx.divider(orientation="vertical", size="2"),
                    rx.vstack(
                        rx.text("Well:", size="1", weight="bold"),
                        rx.text(
                            rx.cond(completion.WellName, completion.WellName, "-"),
                            size="2"
                        ),
                        spacing="0",
                    ),
                    rx.divider(orientation="vertical", size="2"),
                    rx.vstack(
                        rx.text("Reservoir:", size="1", weight="bold"),
                        rx.badge(
                            rx.cond(completion.Reservoir, completion.Reservoir, "-"),
                            color_scheme="blue",
                            size="1"
                        ),
                        spacing="0",
                    ),
                    spacing="3",
                    wrap="wrap",
                )
            ),
            rx.form(
                rx.flex(
                    rx.text("Base Decline Rates (1/month)", size="2", weight="bold", color=rx.color("gray", 11)),
                    rx.grid(
                        rx.flex(
                            rx.text("Do (Oil Decline)", size="2", weight="bold"),
                            rx.input(
                                placeholder="Enter oil decline rate",
                                type="number",
                                name="Do",
                                default_value=completion.Do.to(str),
                                step="0.0000001",
                                width="100%",
                            ),
                            rx.text(f"Current: {completion.Do}", size="1", color=rx.color("gray", 10)),
                            direction="column",
                            spacing="1",
                            width="100%",
                        ),
                        rx.flex(
                            rx.text("Dl (Liquid Decline)", size="2", weight="bold"),
                            rx.input(
                                placeholder="Enter liquid decline rate",
                                type="number",
                                name="Dl",
                                default_value=completion.Dl.to(str),
                                step="0.0000001",
                                width="100%",
                            ),
                            rx.text(f"Current: {completion.Dl}", size="1", color=rx.color("gray", 10)),
                            direction="column",
                            spacing="1",
                            width="100%",
                        ),
                        columns="2",
                        spacing="4",
                        width="100%",
                    ),
                    rx.divider(),
                    rx.text("Decline Adjustment Factors", size="2", weight="bold", color=rx.color("orange", 11)),
                    rx.grid(
                        rx.flex(
                            rx.hstack(
                                rx.text("Dip (Platform Adj.)", size="2", weight="bold"),
                                rx.tooltip(
                                    rx.icon("info", size=12, color=rx.color("gray", 9)),
                                    content="Platform-level adjustment. Applied to all completions on same platform.",
                                ),
                                spacing="1",
                            ),
                            rx.input(
                                placeholder="Platform adjustment factor",
                                type="number",
                                name="Dip",
                                default_value=completion.Dip.to(str),
                                step="0.0000001",
                                width="100%",
                            ),
                            rx.text(f"Current: {completion.Dip}", size="1", color=rx.color("gray", 10)),
                            direction="column",
                            spacing="1",
                            width="100%",
                        ),
                        rx.flex(
                            rx.hstack(
                                rx.text("Dir (Reservoir+Field Adj.)", size="2", weight="bold"),
                                rx.tooltip(
                                    rx.icon("info", size=12, color=rx.color("gray", 9)),
                                    content="Reservoir+Field level adjustment. Different for each reservoir in each field.",
                                ),
                                spacing="1",
                            ),
                            rx.input(
                                placeholder="Reservoir+Field adjustment factor",
                                type="number",
                                name="Dir",
                                default_value=completion.Dir.to(str),
                                step="0.0000001",
                                width="100%",
                            ),
                            rx.text(f"Current: {completion.Dir}", size="1", color=rx.color("gray", 10)),
                            direction="column",
                            spacing="1",
                            width="100%",
                        ),
                        columns="2",
                        spacing="4",
                        width="100%",
                    ),
                    rx.callout(
                        rx.vstack(
                            rx.text("Effective Decline Rate Formula:", size="1", weight="bold"),
                            rx.text("Di_eff = Do × (1 + Dip) × (1 + Dir)", size="1"),
                            spacing="1",
                            align="start",
                        ),
                        icon="calculator",
                        color_scheme="blue",
                        size="1",
                    ),
                    rx.flex(
                        rx.dialog.close(
                            rx.button("Cancel", variant="soft", color_scheme="gray"),
                        ),
                        rx.dialog.close(
                            rx.button("Update", type="submit", color_scheme="blue"),
                        ),
                        spacing="3",
                        justify="end",
                    ),
                    direction="column",
                    spacing="4",
                ),
                on_submit=ProductionState.update_completion,
                reset_on_submit=False,
            ),
            max_width="550px",
        ),
    )
#Search
