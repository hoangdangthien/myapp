"""Global styles for the GTM App."""
import reflex as rx

# Color scheme for oil & gas theme
ACCENT_COLOR = "red"
SIDEBAR_BG = rx.color("gray", 2)
SIDEBAR_HOVER = rx.color("gray", 3)

# Sidebar styles
sidebar_style = {
    "width": "250px",
    "height": "100vh",
    "position": "fixed",
    "left": "0",
    "top": "0",
    "padding": "1em",
    "background": SIDEBAR_BG,
    "border_right": f"1px solid {rx.color('gray', 4)}",
}

# Main content area
content_style = {
    "margin_left": "250px",
    "padding": "2em",
    "min_height": "100vh",
}

# Table styles
table_style = {
    "width": "100%",
}

# Card styles
card_style = {
    "padding": "1.5em",
    "border_radius": "8px",
    "background": rx.color("gray", 2),
    "border": f"1px solid {rx.color('gray', 4)}",
}

# Button styles
primary_button_style = {
    "background": rx.color("accent", 9),
    "color": "white",
}

# Form field styles
form_field_style = {
    "width": "100%",
}

# Graph container styles
graph_container_style = {
    "width": "100%",
    "padding": "1em",
    "border_radius": "8px",
    "background": rx.color("gray", 2),
    "margin_top": "1em",
}
