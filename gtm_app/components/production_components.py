"""Components for Production monitoring page with DCA forecasting.

Updated to include Dip and Dir columns, filter by reservoir.
"""
import reflex as rx
from ..states.production_state import ProductionState
from ..models import CompletionID, RESERVOIR_OPTIONS
from .form_fields import form_field


def completion_filter_controls() -> rx.Component:
    """Filter controls for CompletionID table with reservoir filter."""
    return rx.hstack(
        rx.input(
            rx.input.slot(rx.icon("search")),
            placeholder="Search by ID or Well name...",
            size="1",
            width="200px",
            on_change=ProductionState.filter_completions,
            debounce_timeout=300,
        ),
        
        rx.button(
            rx.icon("refresh-cw", size=14),
            rx.text("Clear", size="1"),
            variant="soft",
            size="1",
            on_click=ProductionState.clear_filters,
        ),
        spacing="2",
        align="center",
    )


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
                    rx.text("Base Decline Rates (1/year)", size="2", weight="bold", color=rx.color("gray", 11)),
                    rx.grid(
                        rx.flex(
                            rx.text("Do (Oil Decline)", size="2", weight="bold"),
                            rx.input(
                                placeholder="Enter oil decline rate",
                                type="number",
                                name="Do",
                                default_value=completion.Do.to(str),
                                step="0.00000001",
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
                                step="0.000000001",
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
                                step="0.0001",
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
                                step="0.0001",
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


def show_completion_row(completion: CompletionID) -> rx.Component:
    """Display a completion in a table row with Dip and Dir columns."""
    return rx.table.row(
        rx.table.cell(
            rx.text(completion.UniqueId, size="1", weight="medium"),
        ),
        rx.table.cell(
            rx.text(
                rx.cond(completion.WellName, completion.WellName, "-"),
                size="1"
            )
        ),
        rx.table.cell(
            rx.badge(
                rx.cond(completion.Reservoir, completion.Reservoir, "-"),
                color_scheme="blue",
                size="1"
            ),
        ),
        rx.table.cell(
            rx.text(
                rx.cond(completion.KH, completion.KH.to(str), "-"),
                size="1"
            )
        ),
        rx.table.cell(
            rx.badge(
                rx.cond(completion.Do, completion.Do.to(str), "-"),
                color_scheme="green",
                size="1"
            ),
        ),
        rx.table.cell(
            rx.badge(
                rx.cond(completion.Dl, completion.Dl.to(str), "-"),
                color_scheme="green",
                size="1"
            ),
        ),
        rx.table.cell(
            rx.badge(
                rx.cond(completion.Dip, completion.Dip.to(str), "0"),
                color_scheme="orange",
                size="1"
            ),
        ),
        rx.table.cell(
            rx.badge(
                rx.cond(completion.Dir, completion.Dir.to(str), "0"),
                color_scheme="purple",
                size="1"
            ),
        ),
        rx.table.cell(
            update_completion_dialog(completion),
        ),
        style={"_hover": {"bg": rx.color("gray", 3)}, "cursor": "pointer"},
        align="center",
        on_click=lambda: ProductionState.set_selected_unique_id(completion.UniqueId),
    )


def completion_table() -> rx.Component:
    """Main CompletionID table component with Dip/Dir columns."""
    return rx.box(
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell(rx.text("Unique ID", size="1", weight="bold")),
                    rx.table.column_header_cell(rx.text("Well Name", size="1", weight="bold")),
                    rx.table.column_header_cell(rx.text("Reservoir", size="1", weight="bold")),
                    rx.table.column_header_cell(rx.text("KH", size="1", weight="bold")),
                    rx.table.column_header_cell(
                        rx.tooltip(
                            rx.text("Do", size="1", weight="bold"),
                            content="Base oil decline rate (1/year)"
                        )
                    ),
                    rx.table.column_header_cell(
                        rx.tooltip(
                            rx.text("Dl", size="1", weight="bold"),
                            content="Base liquid decline rate (1/year)"
                        )
                    ),
                    rx.table.column_header_cell(
                        rx.tooltip(
                            rx.hstack(
                                rx.text("Dip", size="1", weight="bold"),
                                rx.icon("info", size=10, color=rx.color("orange", 9)),
                                spacing="1",
                            ),
                            content="Platform-level decline adjustment factor"
                        )
                    ),
                    rx.table.column_header_cell(
                        rx.tooltip(
                            rx.hstack(
                                rx.text("Dir", size="1", weight="bold"),
                                rx.icon("info", size=10, color=rx.color("purple", 9)),
                                spacing="1",
                            ),
                            content="Reservoir+Field level decline adjustment factor"
                        )
                    ),
                    rx.table.column_header_cell(rx.text("Actions", size="1", weight="bold")),
                ),
            ),
            rx.table.body(
                rx.foreach(
                    ProductionState.completions,
                    show_completion_row
                ),
            ),
            variant="surface",
            size="1",
            width="100%",
        ),
        overflow_x="auto",
        overflow_y="auto",
        max_height="300px",
        width="100%",
    )


def completion_stats_summary() -> rx.Component:
    """Summary statistics cards for completions."""
    return rx.grid(
        rx.card(
            
            rx.hstack(
                rx.icon("layers", size=18, color=rx.color("blue", 9)),
                rx.text(f"Total Completions : {ProductionState.total_completions}", size="2", weight="bold"),
                spacing="2",
                )),
        rx.card(
            rx.hstack(
                    rx.icon("database", size=18, color=rx.color("green", 9)),
                    rx.text(f"History Records: {ProductionState.history_record_count}", size="2", weight="bold"),
                    spacing="2",
                ),
            padding="1em",
        ),
        columns="2",
        spacing="3",
        width="100%",
    )


def selected_completion_info() -> rx.Component:
    """Display selected completion info with DCA parameters including Dip/Dir."""
    return rx.cond(
        ProductionState.selected_unique_id != "",
        rx.card(
            rx.vstack(
                rx.hstack(
                    rx.vstack(
                        rx.text("Selected:", size="1", color=rx.color("gray", 10)),
                        rx.text(ProductionState.selected_unique_id, weight="bold", size="2"),
                        spacing="0",
                    ),
                    rx.divider(orientation="vertical", size="2"),
                    rx.vstack(
                        rx.text("Well:", size="1", color=rx.color("gray", 10)),
                        rx.text(ProductionState.selected_wellname, size="1"),
                        spacing="0",
                    ),
                    rx.divider(orientation="vertical", size="2"),
                    rx.vstack(
                        rx.text("Reservoir:", size="1", color=rx.color("gray", 10)),
                        rx.badge(
                            ProductionState.selected_reservoir_name,
                            color_scheme="blue",
                            size="1"
                        ),
                        spacing="0",
                    ),
                    rx.divider(orientation="vertical", size="2"),
                    rx.vstack(
                        rx.text("Base DCA:", size="1", color=rx.color("gray", 10)),
                        rx.text(ProductionState.dca_parameters_display, size="1"),
                        spacing="0",
                    ),
                    rx.divider(orientation="vertical", size="2"),
                    rx.vstack(
                        rx.text("Adjustments:", size="1", color=rx.color("gray", 10)),
                        rx.hstack(
                            rx.badge(f"Dip: {ProductionState.dip_display}", color_scheme="orange", size="1"),
                            rx.badge(f"Dir: {ProductionState.dir_display}", color_scheme="purple", size="1"),
                            spacing="1",
                        ),
                        spacing="0",
                    ),
                    rx.divider(orientation="vertical", size="2"),
                    rx.vstack(
                        rx.text("Effective Di:", size="1", color=rx.color("gray", 10)),
                        rx.badge(ProductionState.effective_di_display, color_scheme="green", size="1"),
                        spacing="0",
                    ),
                    rx.divider(orientation="vertical", size="2"),
                    forecast_version_selector(),
                    rx.cond(
                        ProductionState.current_forecast_version > 0,
                        rx.button(
                            rx.icon("trash-2", size=12),
                            rx.text("Delete", size="1"),
                            variant="ghost",
                            color_scheme="red",
                            size="1",
                            on_click=ProductionState.delete_current_forecast_version,
                        ),
                        rx.fragment(),
                    ),
                    spacing="3",
                    padding="0.5em",
                    background=rx.color("gray", 2),
                    border_radius="6px",
                    width="100%",
                    align="center",
                    wrap="wrap",
                ),
                # Intervention warning if planned
                rx.cond(
                    ProductionState.has_planned_intervention,
                    rx.hstack(
                        rx.icon("alert-triangle", size=14, color=rx.color("yellow", 9)),
                        rx.text(
                            ProductionState.intervention_info,
                            size="1",
                            color=rx.color("yellow", 11)
                        ),
                        rx.badge("Will save to InterventionProd v0", color_scheme="yellow", size="1"),
                        spacing="2",
                        padding="0.5em",
                        background=rx.color("yellow", 3),
                        border_radius="4px",
                    ),
                    rx.fragment(),
                ),
                spacing="2",
                width="100%",
            ),
            padding="0.75em",
        ),
        rx.text("Select a completion from the table", color=rx.color("gray", 10), size="2"),
    )


def forecast_version_selector() -> rx.Component:
    """Selector for viewing different forecast versions."""
    return rx.cond(
        ProductionState.available_forecast_versions.length() > 0,
        rx.hstack(
            rx.text("Version:", size="1", weight="bold"),
            rx.select(
                ProductionState.forecast_version_options,
                value=ProductionState.current_version_display,
                on_change=ProductionState.set_forecast_version_from_str,
                size="1",
                width="70px",
            ),
            rx.badge(
                ProductionState.version_count_display,
                color_scheme="gray",
                size="1",
            ),
            spacing="2",
            align="center",
        ),
        rx.text("No forecasts", size="1", color=rx.color("gray", 9)),
    )


def batch_update_dip_dialog() -> rx.Component:
    """Dialog for batch updating Dip for all completions on a platform."""
    return rx.dialog.root(
        rx.dialog.trigger(
            rx.button(
                rx.icon("layers", size=14),
                rx.text("Batch Dip", size="1"),
                variant="soft",
                color_scheme="orange",
                size="1",
            ),
        ),
        rx.dialog.content(
            rx.dialog.title("Batch Update Platform Dip"),
            rx.dialog.description(
                "Update Dip value for all completions on a selected platform."
            ),
            rx.form(
                rx.vstack(
                    rx.select(
                        ProductionState.unique_platforms,
                        placeholder="Select Platform",
                        name="platform",
                        required=True,
                        width="100%",
                    ),
                    rx.input(
                        placeholder="New Dip value (e.g., 0.1 for 10% increase)",
                        type="number",
                        name="dip_value",
                        step="0.01",
                        required=True,
                        width="100%",
                    ),
                    rx.callout(
                        "This will update Dip for all completions on the selected platform.",
                        icon="alert-triangle",
                        color_scheme="yellow",
                        size="1",
                    ),
                    rx.flex(
                        rx.dialog.close(
                            rx.button("Cancel", variant="soft", color_scheme="gray"),
                        ),
                        rx.dialog.close(
                            rx.button("Update All", type="submit", color_scheme="orange"),
                        ),
                        spacing="3",
                        justify="end",
                    ),
                    spacing="3",
                    width="100%",
                ),
                on_submit=ProductionState.batch_update_dip,
            ),
            max_width="400px",
        ),
    )


def batch_update_dir_dialog() -> rx.Component:
    """Dialog for batch updating Dir for all completions in a reservoir+field."""
    return rx.dialog.root(
        rx.dialog.trigger(
            rx.button(
                rx.icon("git-branch", size=14),
                rx.text("Batch Dir", size="1"),
                variant="soft",
                color_scheme="purple",
                size="1",
            ),
        ),
        rx.dialog.content(
            rx.dialog.title("Batch Update Reservoir+Field Dir"),
            rx.dialog.description(
                "Update Dir value for all completions in a specific reservoir of a field."
            ),
            rx.form(
                rx.vstack(
                    rx.grid(
                        rx.select(
                            ProductionState.unique_fields,
                            placeholder="Select Field",
                            name="field",
                            required=True,
                            width="100%",
                        ),
                        rx.select(
                            RESERVOIR_OPTIONS,
                            placeholder="Select Reservoir",
                            name="reservoir",
                            required=True,
                            width="100%",
                        ),
                        columns="2",
                        spacing="3",
                        width="100%",
                    ),
                    rx.input(
                        placeholder="New Dir value (e.g., -0.05 for 5% decrease)",
                        type="number",
                        name="dir_value",
                        step="0.01",
                        required=True,
                        width="100%",
                    ),
                    rx.callout(
                        "This will update Dir for all completions in the selected reservoir and field.",
                        icon="alert-triangle",
                        color_scheme="yellow",
                        size="1",
                    ),
                    rx.flex(
                        rx.dialog.close(
                            rx.button("Cancel", variant="soft", color_scheme="gray"),
                        ),
                        rx.dialog.close(
                            rx.button("Update All", type="submit", color_scheme="purple"),
                        ),
                        spacing="3",
                        justify="end",
                    ),
                    spacing="3",
                    width="100%",
                ),
                on_submit=ProductionState.batch_update_dir,
            ),
            max_width="450px",
        ),
    )