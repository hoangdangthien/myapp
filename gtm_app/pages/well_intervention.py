"""Well Intervention (GTM) management page."""
import reflex as rx
from ..templates.template import template
from ..states.gtm_state import GTMState
from ..components.gtm_dialogs import add_gtm_button
from ..components.gtm_table import gtm_table
from ..components.gtm_charts import stats_cards, gtm_type_chart


@template(
    route="/well-intervention",
    title="Well Intervention | GTM Dashboard",
    description="Manage well intervention activities",
    on_load=GTMState.load_gtms,
)
def well_intervention_page() -> rx.Component:
    """Well Intervention management page content.
    
    Features:
    - View all intervention records in table
    - Add new interventions
    - Edit existing interventions
    - Delete interventions
    - View statistics and charts
    """
    return rx.vstack(
        # Page Header
        rx.hstack(
            rx.vstack(
                rx.heading("Well Intervention Management", size="7"),
                rx.text(
                    "Manage and track well intervention activities (GTM)",
                    color=rx.color("gray", 11),
                ),
                align="start",
                spacing="1",
            ),
            rx.spacer(),
            add_gtm_button(),
            width="100%",
            align="center",
        ),
        rx.divider(),
        
        # Statistics Cards
        stats_cards(),
        
        # Charts Section
        rx.grid(
            gtm_type_chart(),
            rx.card(
                rx.vstack(
                    rx.heading("Intervention Timeline", size="4"),
                    rx.text(
                        "Timeline view coming soon",
                        color=rx.color("gray", 11),
                    ),
                    width="100%",
                    align="start",
                    spacing="3",
                    min_height="300px",
                ),
                padding="1.5em",
            ),
            columns="2",
            spacing="4",
            width="100%",
        ),
        
        # Data Table Section
        rx.card(
            rx.vstack(
                rx.hstack(
                    rx.heading("Intervention Records", size="5"),
                    rx.spacer(),
                    rx.hstack(
                        rx.input(
                            placeholder="Search interventions...",
                            width="250px",
                        ),
                        rx.button(
                            rx.icon("filter", size=16),
                            "Filter",
                            variant="soft",
                        ),
                        rx.button(
                            rx.icon("download", size=16),
                            "Export",
                            variant="soft",
                        ),
                        spacing="2",
                    ),
                    width="100%",
                    align="center",
                ),
                rx.divider(),
                gtm_table(),
                width="100%",
                spacing="3",
            ),
            padding="1.5em",
        ),
        
        align="start",
        spacing="4",
        width="100%",
    )
