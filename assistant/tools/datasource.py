"""
Data access layer for the tool registry.

Every loader applies `business_id` at the query layer via
`guards.scoped_query` — tenant isolation lives HERE, not in the tools and never
in the prompt. Tools import this module and call e.g. `datasource.load_sales`,
so tests can monkeypatch a single seam to inject fixtures without MongoDB.
"""
from __future__ import annotations

import pandas as pd

from assistant.guards import scoped_query


def _to_num(series):
    return pd.to_numeric(series.astype(str).str.replace(',', '', regex=False),
                         errors='coerce').fillna(0)


def sales_df_from_records(records: list[dict]) -> pd.DataFrame:
    """Normalize raw sales records into a typed DataFrame (shared by prod + tests)."""
    if not records:
        return pd.DataFrame()
    df = pd.DataFrame(records)
    for c in ('revenue', 'quantity', 'cost'):
        df[c] = _to_num(df[c]) if c in df.columns else 0.0
    date_col = next((c for c in ('date', 'order_date', 'Date') if c in df.columns), None)
    if date_col:
        df['_date'] = pd.to_datetime(df[date_col], errors='coerce').dt.date
    else:
        df['_date'] = None
    # optional hour (some uploads carry a datetime / hour column)
    if 'hour' in df.columns:
        df['_hour'] = _to_num(df['hour']).astype(int)
    elif date_col:
        parsed = pd.to_datetime(df[date_col], errors='coerce')
        df['_hour'] = parsed.dt.hour.where(parsed.dt.hour.gt(0), other=pd.NA)
    else:
        df['_hour'] = pd.NA
    for c in ('item_name', 'category', 'order_type', 'order_id'):
        if c not in df.columns:
            df[c] = None
    return df


# ── Production loaders (tenant-scoped) ───────────────────────────────────────
def load_sales(business_id) -> pd.DataFrame:
    from mongo import collections as col
    records = list(col.sales_records().find(scoped_query(business_id)))
    return sales_df_from_records(records)


def load_inventory(business_id) -> list[dict]:
    from mongo import collections as col
    return list(col.inventory().find(scoped_query(business_id)))


def load_customers(business_id) -> list[dict]:
    from mongo import collections as col
    return list(col.customers().find(scoped_query(business_id)))


def load_menu_items(business_id) -> list[dict]:
    from mongo import collections as col
    return list(col.menu_items().find(scoped_query(business_id)))


def latest_full_analysis(business_id) -> dict | None:
    from mongo import collections as col
    return col.predictions().find_one(
        scoped_query(business_id, {'type': 'full_analysis'}), sort=[('created_at', -1)]
    )


def latest_forecast(business_id) -> dict | None:
    from mongo import collections as col
    return col.predictions().find_one(
        scoped_query(business_id, {'type': 'sales_forecast'}), sort=[('created_at', -1)]
    )


def catalog_names(business_id) -> list[str]:
    """The business's real menu-item names, used for fuzzy entity matching."""
    names: set[str] = set()
    for m in load_menu_items(business_id):
        n = (m.get('name') or m.get('item_name') or '').strip()
        if n:
            names.add(n)
    if not names:  # fall back to distinct item names seen in sales
        df = load_sales(business_id)
        if not df.empty and 'item_name' in df.columns:
            names.update(str(x) for x in df['item_name'].dropna().unique() if str(x).strip())
    return sorted(names)


def category_names(business_id) -> list[str]:
    df = load_sales(business_id)
    if df.empty or 'category' not in df.columns:
        return []
    return sorted({str(x) for x in df['category'].dropna().unique() if str(x).strip()})
