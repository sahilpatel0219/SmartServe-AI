from datetime import datetime, timezone, timedelta, date
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from accounts.models import Membership
from mongo import collections as col
import pandas as pd


def _get_business(request):
    m = Membership.objects.filter(user=request.user, is_active=True).select_related('business').first()
    return (m.business, m) if m else (None, None)


def _load_sales(bid):
    records = list(col.sales_records().find({'business_id': bid}))
    if not records:
        return pd.DataFrame()
    df = pd.DataFrame(records)
    date_col = next((c for c in ['date', 'order_date', 'Date'] if c in df.columns), None)
    rev_col = next((c for c in ['revenue', 'amount', 'Revenue'] if c in df.columns), None)
    cost_col = next((c for c in ['cost', 'cost_price'] if c in df.columns), None)
    item_col = next((c for c in ['item_name', 'item', 'product'] if c in df.columns), None)
    qty_col = next((c for c in ['quantity', 'qty'] if c in df.columns), None)
    if not date_col or not rev_col:
        return pd.DataFrame()
    df['_date'] = pd.to_datetime(df[date_col], errors='coerce')
    df['_revenue'] = pd.to_numeric(df[rev_col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    df['_cost'] = pd.to_numeric(df[cost_col].astype(str).str.replace(',', ''), errors='coerce').fillna(0) if cost_col else 0
    df['_qty'] = pd.to_numeric(df[qty_col].astype(str).str.replace(',', ''), errors='coerce').fillna(0) if qty_col else 0
    df['_item'] = df[item_col].astype(str) if item_col else ''
    return df.dropna(subset=['_date'])


@login_required
def index_view(request):
    business, _ = _get_business(request)
    if not business:
        return redirect('onboarding:create_business')
    bid = business.mongo_id
    df = _load_sales(bid)
    has_data = not df.empty
    if not has_data:
        return render(request, 'analytics/index.html', {
            'business': business, 'has_data': False,
        })

    period = request.GET.get('period', '30')
    days = int(period) if period in ['7', '30', '90', '365'] else 30
    cutoff = pd.Timestamp.now(tz='UTC') - pd.Timedelta(days=days)
    # Make cutoff tz-aware if df dates are tz-naive
    if df['_date'].dt.tz is None:
        cutoff = cutoff.tz_localize(None)
    df_period = df[df['_date'] >= cutoff]

    # Daily revenue for chart
    daily = df_period.groupby(df_period['_date'].dt.date).agg(
        revenue=('_revenue', 'sum'), cost=('_cost', 'sum')
    ).reset_index()
    daily = daily.sort_values('_date')
    daily_labels = [str(d) for d in daily['_date']]
    daily_revenue = [round(v, 2) for v in daily['revenue']]
    daily_profit = [round(r - c, 2) for r, c in zip(daily['revenue'], daily['cost'])]

    # KPI summary
    total_revenue = round(df_period['_revenue'].sum(), 2)
    total_cost = round(df_period['_cost'].sum(), 2)
    total_profit = round(total_revenue - total_cost, 2)
    total_orders = len(df_period)
    avg_order_value = round(total_revenue / total_orders, 2) if total_orders else 0

    # Top items
    if df_period['_item'].any():
        top_items = (
            df_period.groupby('_item').agg(revenue=('_revenue', 'sum'), qty=('_qty', 'sum'))
            .sort_values('revenue', ascending=False).head(8).reset_index()
        )
        top_items_labels = list(top_items['_item'])
        top_items_revenue = [round(v, 2) for v in top_items['revenue']]
    else:
        top_items_labels, top_items_revenue = [], []

    # Day of week heatmap
    df_period_copy = df_period.copy()
    df_period_copy['_dow'] = df_period_copy['_date'].dt.day_name()
    dow_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    dow_rev = df_period_copy.groupby('_dow')['_revenue'].sum()
    dow_data = [round(float(dow_rev.get(d, 0)), 2) for d in dow_order]

    # Hour breakdown (if time data exists)
    hour_data = []
    if df_period['_date'].dt.hour.sum() > 0:
        df_period_copy['_hour'] = df_period_copy['_date'].dt.hour
        hour_rev = df_period_copy.groupby('_hour')['_revenue'].sum()
        hour_data = [{'hour': h, 'revenue': round(float(hour_rev.get(h, 0)), 2)} for h in range(24)]

    # Week-over-week comparison
    prev_cutoff = cutoff - pd.Timedelta(days=days)
    df_prev = df[(df['_date'] >= prev_cutoff) & (df['_date'] < cutoff)]
    prev_revenue = df_prev['_revenue'].sum()
    wow_change = round(((total_revenue - prev_revenue) / prev_revenue * 100) if prev_revenue > 0 else 0, 1)

    period_options = [('7', '7 days'), ('30', '30 days'), ('90', '90 days'), ('365', '1 year')]

    return render(request, 'analytics/index.html', {
        'business': business,
        'has_data': True,
        'period': period,
        'period_options': period_options,
        'kpis': {
            'total_revenue': total_revenue,
            'total_cost': total_cost,
            'total_profit': total_profit,
            'total_orders': total_orders,
            'avg_order_value': avg_order_value,
            'wow_change': wow_change,
        },
        'chart_data': {
            'daily_labels': daily_labels,
            'daily_revenue': daily_revenue,
            'daily_profit': daily_profit,
            'top_items_labels': top_items_labels,
            'top_items_revenue': top_items_revenue,
            'dow_labels': dow_order,
            'dow_data': dow_data,
        },
    })
