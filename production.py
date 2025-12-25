"""GTM Dashboard - Well Intervention Management Application.

A production analysis dashboard for monitoring production data and
evaluating well intervention activities in oil & gas operations.

Features:
- Production monitoring (planned)
- Well intervention (GTM) management
- Decline curve analysis forecasting
- Data visualization with charts

Technology Stack:
- Reflex: Python web framework
- SQLModel: Database ORM
- Recharts: Data visualization
"""
import reflex as rx

# Import all pages - this registers them with the app
from .pages import well_intervention_page


# Create the application with theme configuration
app = rx.App(
    theme=rx.theme(
        radius="medium",
        accent_color="red",  # Oil & gas industry theme
        gray_color="slate",
    ),
    stylesheets=[
        # Add any custom CSS here if needed
    ],
)
