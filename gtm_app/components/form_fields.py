"""Reusable form field components with validation support."""
import reflex as rx
from typing import Optional


# Define validation ranges for different field types
VALIDATION_RANGES = {
    # Production rates (t/day or bbl/day)
    "InitialORate": {"min": 0, "max": 10000, "label": "Initial Oil Rate"},
    "InitialLRate": {"min": 0, "max": 20000, "label": "Initial Liquid Rate"},
    
    # Arps decline parameter b (dimensionless, 0-2 typical)
    "bo": {"min": 0, "max": 2, "label": "b (oil)"},
    "bl": {"min": 0, "max": 2, "label": "b (liquid)"},
    
    # Decline rate Di (1/year, typically 0.001 - 1.0)
    "Dio": {"min": 0, "max": 1, "label": "Di (oil)"},
    "Dil": {"min": 0, "max": 1, "label": "Di (liquid)"},
    "Do": {"min": 0, "max": 1, "label": "Do (oil decline)"},
    "Dl": {"min": 0, "max": 1, "label": "Dl (liquid decline)"},
    
    # KH (permeability-thickness, mD.m)
    "KH": {"min": 0, "max": 100000, "label": "KH"},
    
    # Coordinates
    "X_top": {"min": -1000000, "max": 1000000, "label": "X Top"},
    "Y_top": {"min": -1000000, "max": 1000000, "label": "Y Top"},
    "Z_top": {"min": -10000, "max": 10000, "label": "Z Top"},
    "X_bot": {"min": -1000000, "max": 1000000, "label": "X Bottom"},
    "Y_bot": {"min": -1000000, "max": 1000000, "label": "Y Bottom"},
    "Z_bot": {"min": -10000, "max": 10000, "label": "Z Bottom"},
}


def get_validation_range(field_name: str) -> dict:
    """Get validation range for a field name.
    
    Args:
        field_name: The form field name
        
    Returns:
        Dictionary with min, max, and label keys
    """
    return VALIDATION_RANGES.get(field_name, {"min": None, "max": None, "label": field_name})


def form_field(
    label: str,
    placeholder: str,
    input_type: str,
    name: str,
    default_value: str = "",
    required: bool = True,
    step: str = "0.00001",
    min_value: Optional[float] = None,
    max_value: Optional[float] = None,
    show_range_hint: bool = True,
) -> rx.Component:
    """Create a reusable form field component with validation.
    
    Args:
        label: Field label text
        placeholder: Placeholder text for input
        input_type: HTML input type (text, number, date, etc.)
        name: Form field name for submission
        default_value: Default value for the input
        required: Whether the field is required
        step: Step value for number inputs (use "any" for decimals)
        min_value: Minimum allowed value (for number inputs)
        max_value: Maximum allowed value (for number inputs)
        show_range_hint: Whether to show range hint below input
    
    Returns:
        A Reflex component containing label, input, and optional validation hint
    """
    input_props = {
        "placeholder": placeholder,
        "type": input_type,
        "name": name,
        "default_value": default_value,
        "required": required,
        "width": "100%",
    }
    
    # Get validation range from predefined ranges if not explicitly provided
    if input_type == "number":
        validation = get_validation_range(name)
        
        # Use explicit values if provided, otherwise use predefined
        actual_min = min_value if min_value is not None else validation.get("min")
        actual_max = max_value if max_value is not None else validation.get("max")
        
        input_props["step"] = step
        
        if actual_min is not None:
            input_props["min"] = actual_min
        if actual_max is not None:
            input_props["max"] = actual_max
        
        # Build hint text
        hint_text = ""
        if show_range_hint and (actual_min is not None or actual_max is not None):
            if actual_min is not None and actual_max is not None:
                hint_text = f"Range: {actual_min} - {actual_max}"
            elif actual_min is not None:
                hint_text = f"Min: {actual_min}"
            elif actual_max is not None:
                hint_text = f"Max: {actual_max}"
        
        return rx.flex(
            rx.text(label, size="2", weight="bold"),
            rx.input(**input_props),
            rx.cond(
                hint_text != "",
                rx.text(
                    hint_text,
                    size="1",
                    color=rx.color("gray", 10),
                    style={"font_style": "italic"}
                ),
                rx.fragment(),
            ) if hint_text else rx.fragment(),
            direction="column",
            spacing="1",
            width="100%",
        )
    
    return rx.flex(
        rx.text(label, size="2", weight="bold"),
        rx.input(**input_props),
        direction="column",
        spacing="1",
        width="100%",
    )


def validated_number_field(
    label: str,
    name: str,
    default_value: str = "0",
    required: bool = True,
    step: str = "0.0001",
    min_value: Optional[float] = None,
    max_value: Optional[float] = None,
    placeholder: str = "",
    helper_text: str = "",
) -> rx.Component:
    """Create a validated number input with range constraints.
    
    This component includes:
    - Min/max validation via HTML5 attributes
    - Visual range indicator
    - Optional helper text
    
    Args:
        label: Field label text
        name: Form field name
        default_value: Default value
        required: Whether field is required
        step: Step increment
        min_value: Minimum value (uses predefined if None)
        max_value: Maximum value (uses predefined if None)
        placeholder: Placeholder text
        helper_text: Additional helper text
        
    Returns:
        Validated number input component
    """
    validation = get_validation_range(name)
    actual_min = min_value if min_value is not None else validation.get("min")
    actual_max = max_value if max_value is not None else validation.get("max")
    
    input_props = {
        "type": "number",
        "name": name,
        "default_value": default_value,
        "required": required,
        "step": step,
        "width": "100%",
        "placeholder": placeholder or f"Enter {label.lower()}",
    }
    
    if actual_min is not None:
        input_props["min"] = actual_min
    if actual_max is not None:
        input_props["max"] = actual_max
    
    # Build range display
    range_parts = []
    if actual_min is not None:
        range_parts.append(f"Min: {actual_min}")
    if actual_max is not None:
        range_parts.append(f"Max: {actual_max}")
    range_text = " | ".join(range_parts) if range_parts else ""
    
    return rx.flex(
        rx.hstack(
            rx.text(label, size="2", weight="bold"),
            rx.cond(
                required,
                rx.text("*", size="2", color=rx.color("red", 9)),
                rx.fragment(),
            ),
            spacing="1",
        ),
        rx.input(**input_props),
        rx.hstack(
            rx.cond(
                range_text != "",
                rx.badge(
                    range_text,
                    color_scheme="gray",
                    size="1",
                    variant="soft",
                ),
                rx.fragment(),
            ) if range_text else rx.fragment(),
            rx.cond(
                helper_text != "",
                rx.text(
                    helper_text,
                    size="1",
                    color=rx.color("gray", 10),
                ),
                rx.fragment(),
            ) if helper_text else rx.fragment(),
            spacing="2",
        ),
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


def rate_field(
    label: str,
    name: str,
    default_value: str = "0",
    phase: str = "oil",
) -> rx.Component:
    """Create a production rate input field with appropriate validation.
    
    Args:
        label: Field label
        name: Form field name
        default_value: Default value
        phase: "oil" or "liquid" to set appropriate max
        
    Returns:
        Validated rate input component
    """
    max_val = 10000 if phase == "oil" else 20000
    
    return validated_number_field(
        label=label,
        name=name,
        default_value=default_value,
        min_value=0,
        max_value=max_val,
        step="0.1",
        helper_text="t/day",
    )


def decline_parameter_field(
    label: str,
    name: str,
    default_value: str = "0",
    param_type: str = "b",
) -> rx.Component:
    """Create a decline curve parameter input field.
    
    Args:
        label: Field label
        name: Form field name
        default_value: Default value
        param_type: "b" for Arps b parameter, "di" for decline rate
        
    Returns:
        Validated parameter input component
    """
    if param_type == "b":
        return validated_number_field(
            label=label,
            name=name,
            default_value=default_value,
            min_value=0,
            max_value=2,
            step="0.0001",
            helper_text="Arps exponent (0=exp, 1=harmonic)",
        )
    else:  # di
        return validated_number_field(
            label=label,
            name=name,
            default_value=default_value,
            min_value=0,
            max_value=1,
            step="0.0001",
            helper_text="1/year",
        )