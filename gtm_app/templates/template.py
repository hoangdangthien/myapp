"""Template decorator for consistent page layouts."""
import reflex as rx
from typing import Callable
from ..components.sidebar import sidebar


def template(
    route: str | None = None,
    title: str | None = None,
    description: str | None = None,
    on_load: rx.event.EventHandler | list[rx.event.EventHandler] | None = None,
) -> Callable[[Callable[[], rx.Component]], rx.Component]:
    """Template decorator for creating pages with consistent layout.
    
    This decorator wraps page functions to provide:
    - Sidebar navigation
    - Consistent main content area
    - Page metadata (title, description)
    
    Args:
        route: The route path for the page
        title: Page title for browser tab
        description: Page description for SEO
        on_load: Event handler(s) to run when page loads
    
    Returns:
        Decorated page function
    """
    def decorator(page_fn: Callable[[], rx.Component]) -> rx.Component:
        @rx.page(
            route=route,
            title=title or "Production Dashboard",
            description=description or "Well Intervention Management System",
            on_load=on_load,
        )
        def wrapper() -> rx.Component:
            return rx.box(
                sidebar(),
                rx.box(
                    page_fn(),
                    margin_left="250px",
                    padding="2em",
                    min_height="100vh",
                    width="calc(100% - 250px)",
                ),
                width="100%",
            )
        return wrapper
    return decorator
