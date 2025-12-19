"""Reusable components for GTM App."""
from .sidebar import sidebar
from .form_fields import form_field, select_field
from .gtm_dialogs import add_gtm_button, update_gtm_dialog, delete_gtm_dialog, load_excel_button, search_gtm
from .gtm_table import gtm_table, show_intervention, production_record_table, forecast_result_table, history_stats_card
from .gtm_charts import gtm_type_chart, stats_cards, production_rate_chart
from .production_components import (
    completion_filter_controls,
    completion_table,
    completion_stats_summary,
    selected_completion_info,
    forecast_version_selector,
    update_completion_dialog,
    forecast_controls,
    production_history_table,
    forecast_result_table as prod_forecast_result_table,
    production_rate_chart as prod_production_rate_chart,
)
from .production_tables import (
    forecast_controls as prod_tables_forecast_controls,
    production_history_table as prod_tables_history_table,
    forecast_result_table as prod_tables_forecast_table,
    production_rate_chart as prod_tables_rate_chart,
)