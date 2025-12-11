"""Base state for the GTM App - handles common app-wide state."""
import reflex as rx


class BaseState(rx.State):
    """The base state for the application.
    
    Contains common state variables and methods used across multiple pages.
    """
    
    # Sidebar toggle state
    sidebar_open: bool = True
    
    def toggle_sidebar(self):
        """Toggle the sidebar visibility."""
        self.sidebar_open = not self.sidebar_open
