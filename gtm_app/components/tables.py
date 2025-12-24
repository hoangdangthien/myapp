import reflex as rx
from ..models import *
from ..states.gtm_state import GTMState
from ..states.production_state import ProductionState
from .dialogs import *

#show intervention input table
def show_intervention(Intv: InterventionID) -> rx.Component:
    """Show an intervention in a table row with edit/delete buttons."""
    return rx.table.row(
        rx.table.cell(rx.text(Intv.UniqueId, size="1", weight="medium")),
        rx.table.cell(rx.text(Intv.Field, size="1")),
        rx.table.cell(rx.text(Intv.Platform, size="1")),
        rx.table.cell(rx.text(Intv.Reservoir, size="1")),
        rx.table.cell(rx.badge(Intv.TypeGTM, color_scheme="blue", size="1")),
        rx.table.cell(rx.text(Intv.PlanningDate, size="1")),
        rx.table.cell(
            rx.badge(
                Intv.Status,
                color_scheme=rx.cond(Intv.Status == "Done", "green", rx.cond(Intv.Status == "Plan", "yellow", "gray")),
                size="1"
            )
        ),
        rx.table.cell(rx.text(f"{Intv.InitialORate:.0f}", size="1")),
        rx.table.cell(rx.text(f"{Intv.bo:.2f}", size="1")),
        rx.table.cell(rx.text(f"{Intv.Dio:.3f}", size="1")),
        rx.table.cell(rx.text(f"{Intv.InitialLRate:.0f}", size="1")),
        rx.table.cell(rx.text(f"{Intv.bl:.2f}", size="1")),
        rx.table.cell(rx.text(f"{Intv.Dil:.3f}", size="1")),
        rx.table.cell(rx.hstack(update_intervention_dialog(Intv), delete_intervention_dialog(Intv), spacing="1")),
        style={"_hover": {"bg": rx.color("gray", 3)}},
        align="center",
    )

def intervention_table() -> rx.Component:
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
            rx.table.body(rx.foreach(GTMState.GTM, show_intervention)),
            variant="surface",
            size="1",
            width="100%",
        ),
        overflow_x="auto",
        width="100%",
        max_height="350px",
        overflow_y="auto",
    )

#show production history
def show_production(row)->rx.Component:
    return rx.table.row(
        rx.table.cell(rx.text(row["Date"],size="1")),
        rx.table.cell(rx.text(row["OilRate"],size="1")),
        rx.table.cell(rx.text(row["LiqRate"],size="1")),
        rx.table.cell(rx.text(round(row["Qoil"].to(float)/1000,1),size="1")),
        rx.table.cell(rx.text(round(row["Qliq"].to(float)/1000,1),size="1")),
        rx.table.cell(rx.badge(row["WC"],
                               color_scheme=rx.cond(row["WC"].to(float)>80,"red",rx.cond(row["WC"].to(float)>50,"yellow","green")),
                               size="1")),
        style={"_hover": {"bg": rx.color("gray", 3)}},
        align="center",
    )
def production_header()-> rx.Component:
    return rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell(rx.text("Date", size="1", weight="bold")),
                    rx.table.column_header_cell(rx.text("Oil Rate", size="1", weight="bold")),
                    rx.table.column_header_cell(rx.text("Liq Rate", size="1", weight="bold")),
                    rx.table.column_header_cell(rx.text("Qoil (th.t)", size="1", weight="bold")),
                    rx.table.column_header_cell(rx.text("Qliq (th.t)", size="1", weight="bold")),
                    rx.table.column_header_cell(rx.text("WC %", size="1", weight="bold")),
                ),
            )
def production_table(table_data) -> rx.Component:
    """Table showing production records from HistoryProd for selected intervention."""
    return rx.box(
        rx.table.root(
            production_header(),
            rx.table.body(
                rx.foreach(table_data,show_production), #table data in list of dictionary
            ),
            variant="surface",
            size="1",
            width="100%",
        ),
        overflow_y="auto",
        max_height="250px",
        width="100%",
    )
#show CompletionID
def show_completion_row(completion: CompletionID) -> rx.Component:
    """Display a completion in a table row with Dip and Dir columns."""
    return rx.table.row(
        rx.table.cell(rx.text(completion.UniqueId, size="1", weight="medium"),),
        rx.table.cell(rx.text(rx.cond(completion.WellName, completion.WellName, "-"),size="1")),
        rx.table.cell(rx.badge(rx.cond(completion.Reservoir, completion.Reservoir, "-"),color_scheme="blue",size="1"),),
        rx.table.cell(rx.text(rx.cond(completion.KH, completion.KH.to(str), "-"),size="1")),
        rx.table.cell(rx.badge(rx.cond(completion.Do, completion.Do.to(str), "-"),color_scheme="green",size="1"),),
        rx.table.cell(rx.badge(rx.cond(completion.Dl, completion.Dl.to(str), "-"),color_scheme="green",size="1"),),
        rx.table.cell(rx.badge(rx.cond(completion.Dip, completion.Dip.to(str), "0"),color_scheme="orange",size="1"),),
        rx.table.cell(rx.badge(rx.cond(completion.Dir, completion.Dir.to(str), "0"),color_scheme="purple",size="1"),),
        rx.table.cell(update_completion_dialog(completion),),
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
                            content="Base oil decline rate (1/month)"
                        )
                    ),
                    rx.table.column_header_cell(
                        rx.tooltip(
                            rx.text("Dl", size="1", weight="bold"),
                            content="Base liquid decline rate (1/month)"
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
#Show summary Intervention
def summary_intervention_row(row: dict) -> rx.Component:
    """Render a single row in the summary table."""
    return rx.table.row(
        rx.table.cell(rx.text(row["UniqueId"], size="1", weight="medium")),
        rx.table.cell(rx.text(row["Field"], size="1")),
        rx.table.cell(rx.text(row["Platform"], size="1")),
        rx.table.cell(rx.badge(row["Reservoir"], color_scheme="blue", size="1")),
        rx.table.cell(rx.badge(row["Type"], color_scheme="purple", size="1")),
        rx.table.cell(rx.text(row["Category"], size="1")),
        rx.table.cell(
            rx.badge(
                row["Status"],
                color_scheme=rx.cond(
                    row["Status"] == "Done", 
                    "green", 
                    rx.cond(row["Status"] == "Plan", "yellow", "gray")
                ),
                size="1"
            )
        ),
        rx.table.cell(rx.text(row["Date"], size="1")),
        rx.table.cell(rx.text(row["GTMYear"], size="1")),
        # Monthly Qoil columns
        rx.table.cell(rx.text(row["Jan"], size="1")),
        rx.table.cell(rx.text(row["Feb"], size="1")),
        rx.table.cell(rx.text(row["Mar"], size="1")),
        rx.table.cell(rx.text(row["Apr"], size="1")),
        rx.table.cell(rx.text(row["May"], size="1")),
        rx.table.cell(rx.text(row["Jun"], size="1")),
        rx.table.cell(rx.text(row["Jul"], size="1")),
        rx.table.cell(rx.text(row["Aug"], size="1")),
        rx.table.cell(rx.text(row["Sep"], size="1")),
        rx.table.cell(rx.text(row["Oct"], size="1")),
        rx.table.cell(rx.text(row["Nov"], size="1")),
        rx.table.cell(rx.text(row["Dec"], size="1")),
        rx.table.cell(
            rx.badge(row["Total"], color_scheme="green", size="1", variant="solid")
        ),
        style={"_hover": {"bg": rx.color("gray", 3)}},
        align="center",
    )


def summary_intervention_header() -> rx.Component:
    """Common header for summary tables."""
    return rx.table.header(
        rx.table.row(
            rx.table.column_header_cell(rx.text("UniqueId", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Field", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Platform", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Reservoir", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Type", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Category", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Status", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Date", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("GTMYear", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Jan", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Feb", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Mar", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Apr", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("May", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Jun", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Jul", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Aug", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Sep", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Oct", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Nov", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Dec", size="1", weight="bold")),
            rx.table.column_header_cell(rx.text("Total", size="1", weight="bold")),
        ),
    )


def current_year_intervention_table() -> rx.Component:
    """Summary table for current year Qoil forecast by intervention."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.hstack(
                    rx.icon("calendar", size=18, color=rx.color("blue", 9)),
                    rx.heading(f"Qoil Forecast {GTMState.current_year} (tons)", size="4"),
                    spacing="2",
                    align="center",
                ),
                rx.spacer(),
                rx.hstack(
                    rx.badge(
                        rx.hstack(
                            rx.text("Interventions:", size="1"),
                            rx.text(GTMState.current_year_count, weight="bold", size="1"),
                            spacing="1",
                        ),
                        color_scheme="blue",
                        size="1",
                    ),
                    rx.badge(
                        rx.hstack(
                            rx.text("Total Qoil:", size="1"),
                            rx.text(
                                GTMState.current_year_total_qoil.to(int).to(str),
                                weight="bold",
                                size="1"
                            ),
                            rx.text("t", size="1"),
                            spacing="1",
                        ),
                        color_scheme="green",
                        size="1",
                    ),
                    rx.button(
                        rx.icon("download", size=14),
                        rx.text("Excel", size="1"),
                        on_click=GTMState.download_current_year_excel,
                        size="1",
                        variant="soft",
                        color_scheme="green",
                    ),
                    spacing="2",
                    align="center",
                ),
                width="100%",
                align="center",
            ),
            rx.divider(),
            rx.cond(
                GTMState.current_year_count > 0,
                rx.box(
                    rx.table.root(
                        summary_intervention_header(),
                        rx.table.body(
                            rx.foreach(
                                GTMState.current_year_summary,
                                summary_intervention_row
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
                ),
                rx.center(
                    rx.vstack(
                        rx.icon("inbox", size=32, color=rx.color("gray", 8)),
                        rx.text(
                            "No forecast data for current year",
                            size="2",
                            color=rx.color("gray", 10)
                        ),
                        spacing="2",
                        align="center",
                    ),
                    padding="2em",
                ),
            ),
            width="100%",
            spacing="3",
        ),
        padding="1em",
        width="100%",
    )


def next_year_intervention_table() -> rx.Component:
    """Summary table for next year Qoil forecast by intervention."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.hstack(
                    rx.icon("calendar-plus", size=18, color=rx.color("orange", 9)),
                    rx.heading(f"Qoil Forecast {GTMState.next_year} (tons)", size="4"),
                    spacing="2",
                    align="center",
                ),
                rx.spacer(),
                rx.hstack(
                    rx.badge(
                        rx.hstack(
                            rx.text("Interventions:", size="1"),
                            rx.text(GTMState.next_year_count, weight="bold", size="1"),
                            spacing="1",
                        ),
                        color_scheme="orange",
                        size="1",
                    ),
                    rx.badge(
                        rx.hstack(
                            rx.text("Total Qoil:", size="1"),
                            rx.text(
                                GTMState.next_year_total_qoil.to(int).to(str),
                                weight="bold",
                                size="1"
                            ),
                            rx.text("t", size="1"),
                            spacing="1",
                        ),
                        color_scheme="green",
                        size="1",
                    ),
                    rx.button(
                        rx.icon("download", size=14),
                        rx.text("Excel", size="1"),
                        on_click=GTMState.download_next_year_excel,
                        size="1",
                        variant="soft",
                        color_scheme="green",
                    ),
                    spacing="2",
                    align="center",
                ),
                width="100%",
                align="center",
            ),
            rx.divider(),
            rx.cond(
                GTMState.next_year_count > 0,
                rx.box(
                    rx.table.root(
                        summary_intervention_header(),
                        rx.table.body(
                            rx.foreach(
                                GTMState.next_year_summary,
                                summary_intervention_row
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
                ),
                rx.center(
                    rx.vstack(
                        rx.icon("inbox", size=32, color=rx.color("gray", 8)),
                        rx.text(
                            "No forecast data for next year",
                            size="2",
                            color=rx.color("gray", 10)
                        ),
                        spacing="2",
                        align="center",
                    ),
                    padding="2em",
                ),
            ),
            width="100%",
            spacing="3",
        ),
        padding="1em",
        width="100%",
    )

#Show Production Summary
 
def summary_production_header() -> rx.Component:
    columns = ["UniqueId","Field","Platform","Reservoir","Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec","Total"]
    return rx.table.header(
        rx.table.row(
            *[
                rx.table.column_header_cell(
                    rx.text(col, size="1", weight="bold")
                )
                for col in columns
            ]
        ),
    )
def summary_production_row(row: dict) -> rx.Component:
    return rx.table.row(
        rx.table.cell(rx.text(row["UniqueId"], size="1", weight="medium")),
        rx.table.cell(rx.text(row["Field"], size="1")),
        rx.table.cell(rx.text(row["Platform"], size="1")),
        rx.table.cell(rx.badge(row["Reservoir"], color_scheme="blue", size="1")),
        # Monthly Qoil columns
        rx.table.cell(rx.text(row["Jan"], size="1")),
        rx.table.cell(rx.text(row["Feb"], size="1")),
        rx.table.cell(rx.text(row["Mar"], size="1")),
        rx.table.cell(rx.text(row["Apr"], size="1")),
        rx.table.cell(rx.text(row["May"], size="1")),
        rx.table.cell(rx.text(row["Jun"], size="1")),
        rx.table.cell(rx.text(row["Jul"], size="1")),
        rx.table.cell(rx.text(row["Aug"], size="1")),
        rx.table.cell(rx.text(row["Sep"], size="1")),
        rx.table.cell(rx.text(row["Oct"], size="1")),
        rx.table.cell(rx.text(row["Nov"], size="1")),
        rx.table.cell(rx.text(row["Dec"], size="1")),
        rx.table.cell(
            rx.badge(row["Total"], color_scheme="green", size="1", variant="solid")
        ),
        style={"_hover": {"bg": rx.color("gray", 3)}},
        align="center",
    )

def current_year_production_table() -> rx.Component:
    """Summary table for current year Qoil forecast by intervention."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.hstack(
                    rx.icon("calendar", size=18, color=rx.color("blue", 9)),
                    rx.heading(f"Qoil Forecast {ProductionState.current_year} (tons)", size="4"),
                    spacing="2",
                    align="center",
                ),
                rx.spacer(),
                rx.hstack(
                    rx.badge(
                        rx.hstack(
                            rx.text("Interventions:", size="1"),
                            rx.text(ProductionState.current_year_count, weight="bold", size="1"),
                            spacing="1",
                        ),
                        color_scheme="blue",
                        size="1",
                    ),
                    rx.badge(
                        rx.hstack(
                            rx.text("Total Qoil:", size="1"),
                            rx.text(
                                ProductionState.current_year_total_qoil.to(int).to(str),
                                weight="bold",
                                size="1"
                            ),
                            rx.text("t", size="1"),
                            spacing="1",
                        ),
                        color_scheme="green",
                        size="1",
                    ),
                    rx.button(
                        rx.icon("download", size=14),
                        rx.text("Excel", size="1"),
                        on_click=ProductionState.download_current_year_excel,
                        size="1",
                        variant="soft",
                        color_scheme="green",
                    ),
                    spacing="2",
                    align="center",
                ),
                width="100%",
                align="center",
            ),
            rx.divider(),
            rx.cond(
                ProductionState.current_year_count > 0,
                rx.box(
                    rx.table.root(
                        summary_production_header(),
                        rx.table.body(
                            rx.foreach(
                                ProductionState.current_year_summary,
                                summary_production_row
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
                ),
                rx.center(
                    rx.vstack(
                        rx.icon("inbox", size=32, color=rx.color("gray", 8)),
                        rx.text(
                            "No forecast data for current year",
                            size="2",
                            color=rx.color("gray", 10)
                        ),
                        spacing="2",
                        align="center",
                    ),
                    padding="2em",
                ),
            ),
            width="100%",
            spacing="3",
        ),
        padding="1em",
        width="100%",
    )


def next_year_production_table() -> rx.Component:
    """Summary table for next year Qoil forecast by intervention."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.hstack(
                    rx.icon("calendar-plus", size=18, color=rx.color("orange", 9)),
                    rx.heading(f"Qoil Forecast {ProductionState.next_year} (tons)", size="4"),
                    spacing="2",
                    align="center",
                ),
                rx.spacer(),
                rx.hstack(
                    rx.badge(
                        rx.hstack(
                            rx.text("Interventions:", size="1"),
                            rx.text(ProductionState.next_year_count, weight="bold", size="1"),
                            spacing="1",
                        ),
                        color_scheme="orange",
                        size="1",
                    ),
                    rx.badge(
                        rx.hstack(
                            rx.text("Total Qoil:", size="1"),
                            rx.text(
                                ProductionState.next_year_total_qoil.to(int).to(str),
                                weight="bold",
                                size="1"
                            ),
                            rx.text("t", size="1"),
                            spacing="1",
                        ),
                        color_scheme="green",
                        size="1",
                    ),
                    rx.button(
                        rx.icon("download", size=14),
                        rx.text("Excel", size="1"),
                        on_click=ProductionState.download_next_year_excel,
                        size="1",
                        variant="soft",
                        color_scheme="green",
                    ),
                    spacing="2",
                    align="center",
                ),
                width="100%",
                align="center",
            ),
            rx.divider(),
            rx.cond(
                ProductionState.next_year_count > 0,
                rx.box(
                    rx.table.root(
                        summary_production_header(),
                        rx.table.body(
                            rx.foreach(
                                ProductionState.next_year_summary,
                                summary_production_row
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
                ),
                rx.center(
                    rx.vstack(
                        rx.icon("inbox", size=32, color=rx.color("gray", 8)),
                        rx.text(
                            "No forecast data for next year",
                            size="2",
                            color=rx.color("gray", 10)
                        ),
                        spacing="2",
                        align="center",
                    ),
                    padding="2em",
                ),
            ),
            width="100%",
            spacing="3",
        ),
        padding="1em",
        width="100%",
    )
