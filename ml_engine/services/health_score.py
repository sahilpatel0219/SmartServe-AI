"""
Business Health Score (0–100): composite of 5 components.
All inputs are derived from the business's own uploaded data.
"""
import pandas as pd
from datetime import datetime, timezone, timedelta, date
from mongo import collections as col


def compute_health_score(business_id: str) -> dict:
    scores = {}
    reasons = {}

    # ── 1. Revenue Growth (20 pts) ──────────────────────────────────────────────
    sales = list(col.sales_records().find({'business_id': business_id}))
    if sales:
        df = pd.DataFrame(sales)
        date_col = next((c for c in ['date', 'order_date'] if c in df.columns), None)
        rev_col = next((c for c in ['revenue', 'amount'] if c in df.columns), None)
        if date_col and rev_col:
            df['_date'] = pd.to_datetime(df[date_col], errors='coerce')
            df['_rev'] = pd.to_numeric(df[rev_col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            df = df.dropna(subset=['_date'])
            cutoff = df['_date'].max() - timedelta(days=30)
            recent = df[df['_date'] >= cutoff]['_rev'].sum()
            older = df[df['_date'] < cutoff]['_rev'].sum()
            if older > 0:
                growth = (recent - older) / older * 100
                score = min(20, max(0, 10 + growth * 0.5))
                scores['revenue_growth'] = round(score, 1)
                reasons['revenue_growth'] = f'Revenue {"grew" if growth >= 0 else "declined"} by {abs(growth):.1f}% vs prior period.'
            else:
                scores['revenue_growth'] = 10
                reasons['revenue_growth'] = 'Insufficient history to compare periods.'
        else:
            scores['revenue_growth'] = 0
            reasons['revenue_growth'] = 'Sales data missing date or revenue columns.'
    else:
        scores['revenue_growth'] = 0
        reasons['revenue_growth'] = 'No sales data uploaded.'

    # ── 2. Profit Margin (20 pts) ───────────────────────────────────────────────
    if sales:
        cost_col = next((c for c in ['cost', 'cost_price'] if c in df.columns), None)
        if cost_col:
            df['_cost'] = pd.to_numeric(df[cost_col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            total_rev = df['_rev'].sum()
            total_cost = df['_cost'].sum()
            margin = ((total_rev - total_cost) / total_rev * 100) if total_rev > 0 else 0
            score = min(20, max(0, margin * 0.4))
            scores['profit_margin'] = round(score, 1)
            reasons['profit_margin'] = f'Average margin is {margin:.1f}%.'
        else:
            scores['profit_margin'] = 10
            reasons['profit_margin'] = 'Cost data not provided; margin cannot be computed.'
    else:
        scores['profit_margin'] = 0
        reasons['profit_margin'] = 'No sales data.'

    # ── 3. Inventory Efficiency (20 pts) ────────────────────────────────────────
    inventory = list(col.inventory().find({'business_id': business_id}))
    if inventory:
        inv_df = pd.DataFrame(inventory)
        qty_col = next((c for c in ['quantity', 'qty'] if c in inv_df.columns), None)
        reorder_col = next((c for c in ['reorder_level', 'reorder'] if c in inv_df.columns), None)
        if qty_col and reorder_col:
            inv_df['_qty'] = pd.to_numeric(inv_df[qty_col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            inv_df['_reorder'] = pd.to_numeric(inv_df[reorder_col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            low_stock = (inv_df['_qty'] <= inv_df['_reorder']).sum()
            ratio = 1 - (low_stock / len(inv_df))
            scores['inventory_efficiency'] = round(ratio * 20, 1)
            reasons['inventory_efficiency'] = f'{low_stock}/{len(inv_df)} items are at or below reorder level.'
        else:
            scores['inventory_efficiency'] = 10
            reasons['inventory_efficiency'] = 'Inventory uploaded but missing reorder levels.'
    else:
        scores['inventory_efficiency'] = 5
        reasons['inventory_efficiency'] = 'No inventory data uploaded.'

    # ── 4. Food Waste (20 pts) ──────────────────────────────────────────────────
    waste_pred = col.predictions().find_one(
        {'business_id': business_id, 'type': 'waste_prediction'},
        sort=[('created_at', -1)]
    )
    if waste_pred and 'data' in waste_pred:
        at_risk = len(waste_pred['data'].get('at_risk_items', []))
        inv_total = len(inventory) or 1
        ratio = 1 - min(1, at_risk / inv_total)
        scores['food_waste'] = round(ratio * 20, 1)
        reasons['food_waste'] = f'{at_risk} item(s) at risk of expiry.'
    else:
        scores['food_waste'] = 10
        reasons['food_waste'] = 'Run waste prediction to score this component.'

    # ── 5. Customer Retention (20 pts) ──────────────────────────────────────────
    customers = col.customers().count_documents({'business_id': business_id})
    if customers > 0:
        score = min(20, customers * 0.5)
        scores['customer_retention'] = round(score, 1)
        reasons['customer_retention'] = f'{customers} customer profiles on record.'
    else:
        scores['customer_retention'] = 5
        reasons['customer_retention'] = 'No customer data uploaded.'

    total = round(sum(scores.values()), 1)
    grade = 'A' if total >= 80 else 'B' if total >= 60 else 'C' if total >= 40 else 'D'

    result = {
        'total_score': total,
        'grade': grade,
        'components': scores,
        'reasons': reasons,
        'generated_at': datetime.now(timezone.utc).isoformat(),
    }

    col.predictions().insert_one({
        'business_id': business_id,
        'type': 'health_score',
        'data': result,
        'created_at': datetime.now(timezone.utc),
    })

    return result
