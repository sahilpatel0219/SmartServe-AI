"""
Food waste prediction: identifies inventory items likely to expire
before they can be consumed based on sales velocity vs remaining stock + expiry.
"""
import pandas as pd
from datetime import datetime, date, timezone, timedelta
from mongo import collections as col


def run_waste_prediction(business_id: str) -> dict:
    inventory = list(col.inventory().find({'business_id': business_id}))
    if not inventory:
        raise ValueError('No inventory data for waste prediction.')

    sales = list(col.sales_records().find({'business_id': business_id}))
    df_sales = pd.DataFrame(sales) if sales else pd.DataFrame()

    today = date.today()
    at_risk = []

    for item in inventory:
        name = item.get('item_name') or item.get('name', '')
        qty = float(str(item.get('quantity', 0)).replace(',', '') or 0)
        expiry_raw = item.get('expiry_date', '')
        cost = float(str(item.get('cost_per_unit', 0)).replace(',', '') or 0)

        # Parse expiry
        expiry = None
        if expiry_raw and str(expiry_raw).strip():
            try:
                expiry = pd.to_datetime(str(expiry_raw)).date()
            except Exception:
                pass

        days_until_expiry = (expiry - today).days if expiry else None

        # Estimate daily consumption from sales
        daily_use = 0.0
        if not df_sales.empty:
            item_col = next((c for c in ['item_name', 'item'] if c in df_sales.columns), None)
            qty_col = next((c for c in ['quantity', 'qty'] if c in df_sales.columns), None)
            if item_col and qty_col:
                item_sales = df_sales[df_sales[item_col].astype(str).str.lower() == name.lower()]
                if not item_sales.empty:
                    total_qty = pd.to_numeric(item_sales[qty_col].astype(str).str.replace(',', ''), errors='coerce').fillna(0).sum()
                    date_col = next((c for c in ['date', 'order_date'] if c in df_sales.columns), None)
                    if date_col:
                        n_days = df_sales[date_col].nunique() or 1
                        daily_use = total_qty / n_days

        days_of_stock = (qty / daily_use) if daily_use > 0 else None

        # Flag as at-risk if expiry is within 7 days OR stock lasts > expiry window
        flag = False
        risk_reason = ''
        if days_until_expiry is not None and days_until_expiry <= 7:
            flag = True
            risk_reason = f'Expires in {days_until_expiry} day(s)'
        elif days_of_stock and days_until_expiry and days_of_stock > days_until_expiry:
            flag = True
            risk_reason = f'Stock lasts {days_of_stock:.0f} days but expires in {days_until_expiry} days'

        if flag:
            estimated_loss = round(qty * cost, 2)
            at_risk.append({
                'item': name,
                'quantity': qty,
                'unit': item.get('unit', ''),
                'expiry_date': expiry.isoformat() if expiry else None,
                'days_until_expiry': days_until_expiry,
                'daily_use': round(daily_use, 2),
                'estimated_loss_inr': estimated_loss,
                'risk_reason': risk_reason,
            })

    at_risk.sort(key=lambda x: x.get('days_until_expiry') or 999)
    total_loss = round(sum(i['estimated_loss_inr'] for i in at_risk), 2)

    result = {
        'at_risk_items': at_risk,
        'total_estimated_loss_inr': total_loss,
        'items_checked': len(inventory),
        'generated_at': datetime.now(timezone.utc).isoformat(),
    }

    col.predictions().insert_one({
        'business_id': business_id,
        'type': 'waste_prediction',
        'data': result,
        'created_at': datetime.now(timezone.utc),
    })

    return result
