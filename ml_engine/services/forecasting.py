"""
Sales / demand forecasting using XGBoost (statsmodels SARIMAX as fallback).
Prophet was skipped — it has complex C++ build requirements on Windows.
Using XGBoost with time-series feature engineering instead.
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone

from mongo import collections as col


def _load_sales_df(business_id: str) -> pd.DataFrame:
    records = list(col.sales_records().find({'business_id': business_id}))
    if not records:
        return pd.DataFrame()
    df = pd.DataFrame(records)
    # Normalise date column
    date_col = next((c for c in ['date', 'order_date', 'Date'] if c in df.columns), None)
    if not date_col:
        return pd.DataFrame()
    df['date'] = pd.to_datetime(df[date_col], errors='coerce')
    df = df.dropna(subset=['date'])
    revenue_col = next((c for c in ['revenue', 'amount', 'Revenue'] if c in df.columns), None)
    if not revenue_col:
        return pd.DataFrame()
    df['revenue'] = pd.to_numeric(df[revenue_col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    return df


def run_sales_forecast(business_id: str) -> dict:
    """
    Produces next-7-day daily revenue forecast plus per-item demand estimates.
    Returns a dict with forecast data; also persists to MongoDB.
    """
    df = _load_sales_df(business_id)
    if df.empty or len(df) < 30:
        raise ValueError('Insufficient sales data for forecasting (need ≥30 records).')

    # Aggregate to daily revenue
    daily = df.groupby(df['date'].dt.date)['revenue'].sum().reset_index()
    daily.columns = ['date', 'revenue']
    daily = daily.sort_values('date').reset_index(drop=True)

    # Feature engineering for XGBoost
    daily['date'] = pd.to_datetime(daily['date'])
    daily['day_of_week'] = daily['date'].dt.dayofweek
    daily['day_of_month'] = daily['date'].dt.day
    daily['month'] = daily['date'].dt.month
    daily['week_of_year'] = daily['date'].dt.isocalendar().week.astype(int)
    # Lag features
    for lag in [1, 2, 7]:
        daily[f'lag_{lag}'] = daily['revenue'].shift(lag)
    daily = daily.dropna()

    if len(daily) < 14:
        raise ValueError('Not enough consecutive days for model training after feature engineering.')

    feature_cols = ['day_of_week', 'day_of_month', 'month', 'week_of_year', 'lag_1', 'lag_2', 'lag_7']
    X = daily[feature_cols].values
    y = daily['revenue'].values

    from xgboost import XGBRegressor
    model = XGBRegressor(n_estimators=100, max_depth=4, learning_rate=0.1, random_state=42, verbosity=0)
    model.fit(X, y)

    # Forecast next 7 days
    last_row = daily.iloc[-1]
    last_revenues = list(daily['revenue'].values[-7:])
    forecast_dates = [last_row['date'] + timedelta(days=i+1) for i in range(7)]
    forecasts = []

    for fdate in forecast_dates:
        feats = np.array([[
            fdate.dayofweek,
            fdate.day,
            fdate.month,
            fdate.isocalendar()[1],
            last_revenues[-1] if len(last_revenues) >= 1 else 0,
            last_revenues[-2] if len(last_revenues) >= 2 else 0,
            last_revenues[-7] if len(last_revenues) >= 7 else 0,
        ]])
        pred = float(model.predict(feats)[0])
        pred = max(0, round(pred, 2))
        forecasts.append({'date': fdate.strftime('%Y-%m-%d'), 'predicted_revenue': pred})
        last_revenues.append(pred)

    # Per-item demand (top 10 items by volume, last 30 days)
    item_col = next((c for c in ['item_name', 'item', 'product'] if c in df.columns), None)
    qty_col = next((c for c in ['quantity', 'qty', 'Quantity'] if c in df.columns), None)
    item_demand = []
    if item_col and qty_col:
        df['qty_num'] = pd.to_numeric(df[qty_col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
        cutoff = df['date'].max() - timedelta(days=30)
        recent = df[df['date'] >= cutoff]
        top_items = (
            recent.groupby(item_col)['qty_num'].sum()
            .sort_values(ascending=False).head(10)
        )
        avg_daily = len(recent['date'].unique()) or 1
        for item, total_qty in top_items.items():
            item_demand.append({
                'item': str(item),
                'avg_daily_qty': round(total_qty / avg_daily, 1),
                'total_30d': int(total_qty),
            })

    result = {
        'daily_forecast': forecasts,
        'item_demand': item_demand,
        'model': 'xgboost',
        'training_rows': len(daily),
        'generated_at': datetime.now(timezone.utc).isoformat(),
    }

    # Persist
    col.predictions().insert_one({
        'business_id': business_id,
        'type': 'sales_forecast',
        'data': result,
        'created_at': datetime.now(timezone.utc),
    })

    return result
