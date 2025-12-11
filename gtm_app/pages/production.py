"""Production monitoring page."""
import reflex as rx
from ..templates.template import template


@template(
    route="/",
    title="Production | GTM Dashboard",
    description="Production monitoring and analysis",
)
def production_page() -> rx.Component:
    """Production monitoring page content.
    
    This page will contain:
    - Production rate monitoring charts
    - Cumulative production tracking
    - Decline curve analysis
    - Production forecasting
    """
    return rx.vstack(
        rx.hstack(
            rx.heading("Production Monitoring", size="7"),
            rx.spacer(),
            rx.badge("Coming Soon", color_scheme="blue", size="2"),
            width="100%",
            align="center",
        ),
        rx.divider(),
        rx.card(
            rx.vstack(
                rx.icon("bar-chart-3", size=48, color=rx.color("gray", 8)),
                rx.heading("Production Dashboard", size="5"),
                rx.text(
                    "This page will contain production monitoring features including:",
                    color=rx.color("gray", 11),
                    text_align="center",
                ),
                rx.vstack(
                    rx.hstack(
                        rx.icon("trending-up", size=16),
                        rx.text("Real-time production rate monitoring"),
                    ),
                    rx.hstack(
                        rx.icon("line-chart", size=16),
                        rx.text("Decline curve analysis (DCA)"),
                    ),
                    rx.hstack(
                        rx.icon("calculator", size=16),
                        rx.text("Production forecasting with Arps model"),
                    ),
                    rx.hstack(
                        rx.icon("layers", size=16),
                        rx.text("Field-level and well-level aggregation"),
                    ),
                    align="start",
                    spacing="2",
                ),
                align="center",
                spacing="4",
                padding="3em",
            ),
            width="100%",
        ),
        rx.grid(
            rx.card(
                rx.vstack(
                    rx.heading("Oil Production", size="4"),
                    rx.text("0 bbl/day", size="6", weight="bold"),
                    rx.text("Total: 0 bbl", size="2", color=rx.color("gray", 11)),
                    align="center",
                    padding="1.5em",
                ),
            ),
            rx.card(
                rx.vstack(
                    rx.heading("Liquid Production", size="4"),
                    rx.text("0 bbl/day", size="6", weight="bold"),
                    rx.text("Total: 0 bbl", size="2", color=rx.color("gray", 11)),
                    align="center",
                    padding="1.5em",
                ),
            ),
            rx.card(
                rx.vstack(
                    rx.heading("Water Cut", size="4"),
                    rx.text("0 %", size="6", weight="bold"),
                    rx.text("Average", size="2", color=rx.color("gray", 11)),
                    align="center",
                    padding="1.5em",
                ),
            ),
            columns="3",
            spacing="4",
            width="100%",
        ),
        align="start",
        spacing="4",
        width="100%",
    )
