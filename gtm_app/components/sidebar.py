"""Sidebar component for navigation."""
import reflex as rx
from ..styles import SIDEBAR_BG, SIDEBAR_HOVER


def sidebar_item(
    text: str, 
    icon: str, 
    href: str,
    is_active: bool = False
) -> rx.Component:
    """Create a sidebar navigation item."""
    return rx.link(
        rx.hstack(
            rx.icon(icon, size=20),
            rx.text(text, size="3", weight="medium"),
            width="100%",
            padding="0.75em",
            border_radius="8px",
            background=rx.cond(
                is_active,
                rx.color("accent", 3),
                "transparent"
            ),
            _hover={"background": SIDEBAR_HOVER},
            spacing="3",
        ),
        href=href,
        width="100%",
        style={"text_decoration": "none"},
    )


def sidebar_header() -> rx.Component:
    """Create the sidebar header with logo and title."""
    return rx.hstack(
        rx.icon("droplet", size=28, color=rx.color("accent", 9)),
        rx.text(
            "Production Dashboard",
            size="5",
            weight="bold",
        ),
        spacing="2",
        padding="1em",
        margin_bottom="1em",
    )


def sidebar() -> rx.Component:
    """Create the main sidebar navigation component."""
    return rx.box(
        rx.vstack(
            sidebar_header(),
            rx.divider(),
            rx.vstack(
                sidebar_item(
                    "Production",
                    "bar-chart-3",
                    "/",
                ),
                sidebar_item(
                    "Well Intervention",
                    "wrench",
                    "/well-intervention",
                ),
                
                width="100%",
                spacing="1",
                padding="0.5em",
            ),
            rx.spacer(),
            rx.divider(),
            rx.hstack(
                rx.icon("settings", size=18),
                rx.text("Settings", size="2"),
                padding="1em",
                spacing="2",
                _hover={"background": SIDEBAR_HOVER, "cursor": "pointer"},
                border_radius="8px",
            ),
            width="100%",
            height="100vh",
            align="start",
        ),
        width="250px",
        height="100vh",
        position="fixed",
        left="0",
        top="0",
        padding="0.5em",
        background=SIDEBAR_BG,
        border_right=f"1px solid {rx.color('gray', 4)}",
    )