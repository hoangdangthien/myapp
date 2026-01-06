"""Pagination components for CompletionID and InterventionID tables.

Provides reusable pagination controls following Reflex best practices.
Uses offset/limit pattern for database-backed pagination.
"""
import reflex as rx
from typing import Callable


def pagination_controls(
    current_page: rx.Var,
    total_pages: rx.Var,
    page_size: rx.Var,
    total_count: rx.Var,
    on_prev: Callable,
    on_next: Callable,
    on_page_size_change: Callable,
    page_size_options: list = [10, 20, 50, 100],
) -> rx.Component:
    """Reusable pagination controls component.
    
    Args:
        current_page: Current page number (1-indexed)
        total_pages: Total number of pages
        page_size: Items per page
        total_count: Total number of items
        on_prev: Callback for previous page
        on_next: Callback for next page
        on_page_size_change: Callback for page size change
        page_size_options: List of available page sizes
        
    Returns:
        Pagination controls component
    """
    return rx.hstack(
        # Page size selector
        rx.hstack(
            rx.text("Show:", size="1", color=rx.color("gray", 11)),
            rx.select(
                [str(opt) for opt in page_size_options],
                value=page_size.to(str),
                on_change=on_page_size_change,
                size="1",
                width="70px",
            ),
            rx.text("items", size="1", color=rx.color("gray", 11)),
            spacing="2",
            align="center",
        ),
        rx.spacer(),
        # Navigation controls
        rx.hstack(
            rx.button(
                rx.icon("chevrons-left", size=14),
                variant="soft",
                size="1",
                disabled=current_page <= 1,
                on_click=lambda: on_prev("first"),
                title="First page",
            ),
            rx.button(
                rx.icon("chevron-left", size=14),
                variant="soft",
                size="1",
                disabled=current_page <= 1,
                on_click=lambda: on_prev("prev"),
                title="Previous page",
            ),
            rx.hstack(
                rx.text(
                    f"Page ",
                    size="1",
                    color=rx.color("gray", 11),
                ),
                rx.text(
                    current_page.to(str),
                    size="1",
                    weight="bold",
                ),
                rx.text(
                    " / ",
                    size="1",
                    color=rx.color("gray", 11),
                ),
                rx.text(
                    total_pages.to(str),
                    size="1",
                    weight="bold",
                ),
                spacing="1",
                align="center",
            ),
            rx.button(
                rx.icon("chevron-right", size=14),
                variant="soft",
                size="1",
                disabled=current_page >= total_pages,
                on_click=lambda: on_next("next"),
                title="Next page",
            ),
            rx.button(
                rx.icon("chevrons-right", size=14),
                variant="soft",
                size="1",
                disabled=current_page >= total_pages,
                on_click=lambda: on_next("last"),
                title="Last page",
            ),
            spacing="1",
            align="center",
        ),
        rx.spacer(),
        # Total count display
        rx.text(
            f"Total: {total_count} items",
            size="1",
            color=rx.color("gray", 11),
        ),
        width="100%",
        align="center",
        spacing="3",
        padding_y="0.5em",
    )


def simple_pagination_controls(
    current_page: rx.Var,
    total_pages: rx.Var,
    on_prev: Callable,
    on_next: Callable,
) -> rx.Component:
    """Simple pagination with just prev/next buttons.
    
    Args:
        current_page: Current page number (1-indexed)
        total_pages: Total number of pages
        on_prev: Callback for previous page
        on_next: Callback for next page
        
    Returns:
        Simple pagination controls component
    """
    return rx.hstack(
        rx.button(
            rx.icon("chevron-left", size=14),
            rx.text("Prev", size="1"),
            variant="soft",
            size="1",
            disabled=current_page <= 1,
            on_click=on_prev,
        ),
        rx.text(
            current_page.to(str),
            size="1",
            weight="bold",
        ),
        rx.text(
            " / ",
            size="1",
            color=rx.color("gray", 10),
        ),
        rx.text(
            total_pages.to(str),
            size="1",
            weight="bold",
        ),
        rx.button(
            rx.text("Next", size="1"),
            rx.icon("chevron-right", size=14),
            variant="soft",
            size="1",
            disabled=current_page >= total_pages,
            on_click=on_next,
        ),
        spacing="2",
        align="center",
        justify="center",
    )


def pagination_info(
    start_item: rx.Var,
    end_item: rx.Var,
    total_count: rx.Var,
) -> rx.Component:
    """Display pagination info (showing X-Y of Z items).
    
    Args:
        start_item: First item index on current page
        end_item: Last item index on current page
        total_count: Total number of items
        
    Returns:
        Pagination info text component
    """
    return rx.text(
        f"Showing {start_item} - {end_item} of {total_count}",
        size="1",
        color=rx.color("gray", 11),
    )