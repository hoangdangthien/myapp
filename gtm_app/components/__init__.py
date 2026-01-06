"""Reusable components for GTM App."""
# Shared components
from .shared_tables import (
    production_table_header,
    wc_badge,
    status_badge,
    scrollable_table_container,
    history_table_row,
    forecast_table_row,
    create_history_table,
    create_forecast_table,
    stats_info_card,
    version_selector,
    loading_spinner,
    empty_state,
)

from .shared_charts import (
    chart_toggle_controls,
    dual_axis_line_chart,
    chart_legend,
    production_chart_card,
    bar_chart_simple,
)

# Original components (import only if they exist)
try:
    from .sidebar import sidebar
except ImportError:
    pass

try:
    from .form_fields import form_field, select_field
except ImportError:
    pass

from .dialogs import *
from .charts import *
from .statistics import *
try:
    from .block_summary_components import (
        block_summary_controls,
        current_year_summary_table as block_current_year_table,
        next_year_summary_table as block_next_year_table,
        detailed_summary_table,
    )
except ImportError:
    pass