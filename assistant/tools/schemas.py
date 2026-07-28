"""
Tool registry + LLM-facing function schemas.

`REGISTRY[name]` = {fn, description, parameters, financial}. `business_id` and
`role` are NEVER part of a schema — the orchestrator injects them server-side,
so the model cannot supply or override the tenant.
"""
from __future__ import annotations

from . import functions as fn

_DATE = {'type': 'string', 'description': 'ISO date YYYY-MM-DD'}
_METRIC = {'type': 'string', 'enum': ['revenue', 'orders', 'quantity', 'profit', 'margin', 'cost']}

REGISTRY: dict[str, dict] = {
    'get_metric': {
        'fn': fn.get_metric, 'financial': True,
        'description': 'Total of a metric over a date range, optionally for one item or category.',
        'parameters': {
            'metric': _METRIC, 'start': _DATE, 'end': _DATE,
            'item': {'type': 'string'}, 'category': {'type': 'string'},
        },
        'required': ['metric', 'start', 'end'],
    },
    'compare_periods': {
        'fn': fn.compare_periods, 'financial': True,
        'description': 'Compare a metric between two date periods; returns both values, delta and % change.',
        'parameters': {
            'metric': _METRIC,
            'period_a': {'type': 'array', 'description': '[start, end] ISO dates'},
            'period_b': {'type': 'array', 'description': '[start, end] ISO dates'},
            'item': {'type': 'string'},
        },
        'required': ['metric', 'period_a', 'period_b'],
    },
    'rank_items': {
        'fn': fn.rank_items, 'financial': True,
        'description': 'Rank menu items by a metric over a range (top or bottom).',
        'parameters': {
            'metric': _METRIC, 'start': _DATE, 'end': _DATE,
            'limit': {'type': 'integer', 'default': 5},
            'ascending': {'type': 'boolean', 'description': 'True for worst/bottom items'},
        },
        'required': ['metric', 'start', 'end'],
    },
    'get_trend': {
        'fn': fn.get_trend, 'financial': True,
        'description': 'Time series of a metric across a range, bucketed by day/week/month.',
        'parameters': {'metric': _METRIC, 'start': _DATE, 'end': _DATE,
                       'granularity': {'type': 'string', 'enum': ['day', 'week', 'month']}},
        'required': ['metric', 'start', 'end'],
    },
    'get_sales_breakdown': {
        'fn': fn.get_sales_breakdown, 'financial': False,
        'description': 'Break revenue down by day/weekday/category/hour over a range.',
        'parameters': {'start': _DATE, 'end': _DATE,
                       'by': {'type': 'string', 'enum': ['day', 'weekday', 'category', 'hour']}},
        'required': ['start', 'end'],
    },
    'get_low_stock': {
        'fn': fn.get_low_stock, 'financial': False,
        'description': 'Inventory items at or below their reorder level.', 'parameters': {}, 'required': [],
    },
    'get_expiring_soon': {
        'fn': fn.get_expiring_soon, 'financial': False,
        'description': 'Inventory items expiring within N days.',
        'parameters': {'days': {'type': 'integer', 'default': 3}}, 'required': [],
    },
    'get_reorder_suggestions': {
        'fn': fn.get_reorder_suggestions, 'financial': False,
        'description': 'Items to reorder now with a suggested quantity.', 'parameters': {}, 'required': [],
    },
    'get_forecast': {
        'fn': fn.get_forecast, 'financial': False,
        'description': 'Latest sales forecast with confidence/error and history length.',
        'parameters': {'horizon': {'type': 'integer', 'default': 7}, 'item': {'type': 'string'}}, 'required': [],
    },
    'get_item_profitability': {
        'fn': fn.get_item_profitability, 'financial': True,
        'description': 'Per-item revenue, cost, profit and margin.',
        'parameters': {'item': {'type': 'string'}}, 'required': [],
    },
    'get_waste_risk': {
        'fn': fn.get_waste_risk, 'financial': False,
        'description': 'Estimated food-waste loss and at-risk items.', 'parameters': {}, 'required': [],
    },
    'get_customer_stats': {
        'fn': fn.get_customer_stats, 'financial': False,
        'description': 'Customer counts by segment and top spenders (aggregates only).',
        'parameters': {'segment': {'type': 'string', 'enum': ['VIP', 'Regular', 'Inactive']}}, 'required': [],
    },
    'get_peak_times': {
        'fn': fn.get_peak_times, 'financial': False,
        'description': 'Busiest weekdays (and hours if available) by revenue.',
        'parameters': {'start': _DATE, 'end': _DATE}, 'required': [],
    },
    'get_health_score': {
        'fn': fn.get_health_score, 'financial': False,
        'description': 'Business health score (0–100) with component breakdown.', 'parameters': {}, 'required': [],
    },
    'get_data_availability': {
        'fn': fn.get_data_availability, 'financial': False,
        'description': 'What data is uploaded, its date coverage and gaps.', 'parameters': {}, 'required': [],
    },
    'explain_sales_change': {
        'fn': fn.explain_sales_change, 'financial': False,
        'description': 'Diagnose why revenue changed for a period — decomposes the change by item '
                       'and flags untracked factors. Use for "why" questions.',
        'parameters': {'period_a': {'type': 'array', 'description': '[start, end] ISO dates to explain'},
                       'period_b': {'type': 'array', 'description': 'optional [start, end] baseline'}},
        'required': ['period_a'],
    },
}


def tool_schemas() -> list[dict]:
    """OpenAI/Anthropic-style function schemas (business_id/role excluded)."""
    out = []
    for name, spec in REGISTRY.items():
        out.append({
            'name': name,
            'description': spec['description'],
            'parameters': {
                'type': 'object',
                'properties': spec['parameters'],
                'required': spec.get('required', []),
            },
        })
    return out
