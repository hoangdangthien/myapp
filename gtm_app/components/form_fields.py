"""Reusable form field components."""
import reflex as rx


def form_field(
    label: str,
    placeholder: str,
    input_type: str,
    name: str,
    default_value: str = "",
    required: bool = True,
    step: str = "any",  # Add step parameter for number inputs
) -> rx.Component:
    """Create a reusable form field component.
    
    Args:
        label: Field label text
        placeholder: Placeholder text for input
        input_type: HTML input type (text, number, date, etc.)
        name: Form field name for submission
        default_value: Default value for the input
        required: Whether the field is required
        step: Step value for number inputs (use "any" for decimals)
    
    Returns:
        A Reflex component containing label and input
    """
    input_props = {
        "placeholder": placeholder,
        "type": input_type,
        "name": name,
        "default_value": default_value,
        "required": required,
        "width": "100%",
    }
    
    # Add step attribute for number inputs to allow decimals
    if input_type == "number":
        input_props["step"] = step
    
    return rx.flex(
        rx.text(label, size="2", weight="bold"),
        rx.input(**input_props),
        direction="column",
        spacing="1",
        width="100%",
    )


def select_field(
    label: str,
    options: list[str],
    name: str,
    default_value: str = "",
) -> rx.Component:
    """Create a reusable select/dropdown field component.
    
    Args:
        label: Field label text
        options: List of options for the dropdown
        name: Form field name for submission
        default_value: Default selected value
    
    Returns:
        A Reflex component containing label and select
    """
    return rx.flex(
        rx.text(label, size="2", weight="bold"),
        rx.select(
            options,
            name=name,
            default_value=default_value,
            required=True,
            width="100%",
        ),
        direction="column",
        spacing="1",
        width="100%",
    )