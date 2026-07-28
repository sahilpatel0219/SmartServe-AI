"""
Deterministic analytics tool registry.

Every tool is a plain Python function that queries the business's real data and
returns a STRUCTURED result (values + the date window used + a `data_sufficient`
flag) — never a formatted string, and never a number the LLM made up. The
orchestrator injects `business_id` (from the session) and `role`; the LLM only
chooses the tool and its analytical arguments.

`REGISTRY` maps tool name → {fn, schema} for LLM function-calling (step 4).
"""
from . import functions as _fn
from .schemas import REGISTRY, tool_schemas  # noqa: F401

# Re-export the tool functions for direct use by the orchestrator / tests.
get_metric = _fn.get_metric
compare_periods = _fn.compare_periods
rank_items = _fn.rank_items
get_trend = _fn.get_trend
get_sales_breakdown = _fn.get_sales_breakdown
get_low_stock = _fn.get_low_stock
get_expiring_soon = _fn.get_expiring_soon
get_reorder_suggestions = _fn.get_reorder_suggestions
get_forecast = _fn.get_forecast
get_item_profitability = _fn.get_item_profitability
get_waste_risk = _fn.get_waste_risk
get_customer_stats = _fn.get_customer_stats
get_peak_times = _fn.get_peak_times
get_health_score = _fn.get_health_score
get_data_availability = _fn.get_data_availability
explain_sales_change = _fn.explain_sales_change
