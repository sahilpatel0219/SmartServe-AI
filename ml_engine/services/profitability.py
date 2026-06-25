"""
Per-item profitability: revenue, cost, margin.
Classifies items as Stars / Puzzles / Dogs / Plowhorses (menu engineering matrix).
"""
import pandas as pd
from datetime import datetime, timezone
from mongo import collections as col


def run_profitability_analysis(business_id: str) -> dict:
    sales = list(col.sales_records().find({'business_id': business_id}))
    if not sales:
        raise ValueError('No sales data available for profitability analysis.')

    df = pd.DataFrame(sales)

    item_col = next((c for c in ['item_name', 'item', 'product'] if c in df.columns), None)
    revenue_col = next((c for c in ['revenue', 'amount'] if c in df.columns), None)
    cost_col = next((c for c in ['cost', 'cost_price'] if c in df.columns), None)
    qty_col = next((c for c in ['quantity', 'qty'] if c in df.columns), None)

    if not item_col or not revenue_col:
        raise ValueError('Sales data must have item_name and revenue columns for profitability analysis.')

    df['_revenue'] = pd.to_numeric(df[revenue_col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    df['_cost'] = pd.to_numeric(df[cost_col].astype(str).str.replace(',', ''), errors='coerce').fillna(0) if cost_col else 0
    df['_qty'] = pd.to_numeric(df[qty_col].astype(str).str.replace(',', ''), errors='coerce').fillna(1) if qty_col else 1

    grouped = df.groupby(item_col).agg(
        total_revenue=('_revenue', 'sum'),
        total_cost=('_cost', 'sum'),
        total_qty=('_qty', 'sum'),
    ).reset_index()

    grouped['avg_price'] = (grouped['total_revenue'] / grouped['total_qty'].replace(0, 1)).round(2)
    grouped['avg_cost'] = (grouped['total_cost'] / grouped['total_qty'].replace(0, 1)).round(2)
    grouped['margin'] = ((grouped['total_revenue'] - grouped['total_cost']) / grouped['total_revenue'].replace(0, 1) * 100).round(1)
    grouped['profit'] = (grouped['total_revenue'] - grouped['total_cost']).round(2)

    # Menu engineering: classify by popularity (qty) and margin
    qty_median = grouped['total_qty'].median()
    margin_median = grouped['margin'].median()

    def classify(row):
        high_pop = row['total_qty'] >= qty_median
        high_margin = row['margin'] >= margin_median
        if high_pop and high_margin:
            return 'Star'
        elif high_pop and not high_margin:
            return 'Plowhorse'
        elif not high_pop and high_margin:
            return 'Puzzle'
        else:
            return 'Dog'

    grouped['classification'] = grouped.apply(classify, axis=1)

    items = grouped.sort_values('total_revenue', ascending=False).to_dict(orient='records')
    # Sanitise item keys
    clean_items = [{
        'item': str(r[item_col]),
        'total_revenue': round(r['total_revenue'], 2),
        'total_cost': round(r['total_cost'], 2),
        'profit': round(r['profit'], 2),
        'margin_pct': round(r['margin'], 1),
        'total_qty': int(r['total_qty']),
        'classification': r['classification'],
    } for r in items]

    result = {
        'items': clean_items,
        'total_revenue': round(grouped['total_revenue'].sum(), 2),
        'total_cost': round(grouped['total_cost'].sum(), 2),
        'total_profit': round(grouped['profit'].sum(), 2),
        'overall_margin': round(grouped['margin'].mean(), 1),
        'generated_at': datetime.now(timezone.utc).isoformat(),
    }

    col.predictions().insert_one({
        'business_id': business_id,
        'type': 'profitability',
        'data': result,
        'created_at': datetime.now(timezone.utc),
    })

    return result
