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

try:
    from .gtm_dialogs import (
        add_gtm_button, 
        update_gtm_dialog, 
        delete_gtm_dialog, 
        load_excel_button, 
        search_gtm
    )
except ImportError:
    pass

try:
    from .gtm_table import (
        gtm_table, 
        show_intervention, 
        production_record_table, 
        forecast_result_table, 
        history_stats_card
    )
except ImportError:
    pass

try:
    from .gtm_charts import gtm_type_chart, stats_cards, production_rate_chart
except ImportError:
    pass

try:
    from .summary_tables import (
        current_year_summary_table,
        next_year_summary_table,
        summary_section,
        download_all_button,
    )
except ImportError:
    pass