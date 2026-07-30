import pandas as pd
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from analytics.views import _load_sales
from .tenancy import require_business


class AnalyticsView(APIView):
    """Same computation as analytics.views.index_view, returned as JSON."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        business, _ = require_business(request)
        df = _load_sales(business.mongo_id)
        if df.empty:
            return Response({'has_data': False})

        period = request.query_params.get('period', '30')
        days = int(period) if period in ['7', '30', '90', '365'] else 30
        cutoff = pd.Timestamp.now(tz='UTC') - pd.Timedelta(days=days)
        if df['_date'].dt.tz is None:
            cutoff = cutoff.tz_localize(None)
        df_period = df[df['_date'] >= cutoff]

        daily = df_period.groupby(df_period['_date'].dt.date).agg(
            revenue=('_revenue', 'sum'), cost=('_cost', 'sum')
        ).reset_index().sort_values('_date')
        daily_labels = [str(d) for d in daily['_date']]
        daily_revenue = [round(v, 2) for v in daily['revenue']]
        daily_profit = [round(r - c, 2) for r, c in zip(daily['revenue'], daily['cost'])]

        total_revenue = round(df_period['_revenue'].sum(), 2)
        total_cost = round(df_period['_cost'].sum(), 2)
        total_profit = round(total_revenue - total_cost, 2)
        total_orders = len(df_period)
        avg_order_value = round(total_revenue / total_orders, 2) if total_orders else 0

        if df_period['_item'].any():
            top_items = (
                df_period.groupby('_item').agg(revenue=('_revenue', 'sum'), qty=('_qty', 'sum'))
                .sort_values('revenue', ascending=False).head(8).reset_index()
            )
            top_items_labels = list(top_items['_item'])
            top_items_revenue = [round(v, 2) for v in top_items['revenue']]
        else:
            top_items_labels, top_items_revenue = [], []

        df_period_copy = df_period.copy()
        df_period_copy['_dow'] = df_period_copy['_date'].dt.day_name()
        dow_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        dow_rev = df_period_copy.groupby('_dow')['_revenue'].sum()
        dow_data = [round(float(dow_rev.get(d, 0)), 2) for d in dow_order]

        hour_data = []
        if df_period['_date'].dt.hour.sum() > 0:
            df_period_copy['_hour'] = df_period_copy['_date'].dt.hour
            hour_rev = df_period_copy.groupby('_hour')['_revenue'].sum()
            hour_data = [{'hour': h, 'revenue': round(float(hour_rev.get(h, 0)), 2)} for h in range(24)]

        prev_cutoff = cutoff - pd.Timedelta(days=days)
        df_prev = df[(df['_date'] >= prev_cutoff) & (df['_date'] < cutoff)]
        prev_revenue = df_prev['_revenue'].sum()
        wow_change = round(((total_revenue - prev_revenue) / prev_revenue * 100) if prev_revenue > 0 else 0, 1)

        return Response({
            'has_data': True,
            'period': period,
            'kpis': {
                'total_revenue': total_revenue, 'total_cost': total_cost, 'total_profit': total_profit,
                'total_orders': total_orders, 'avg_order_value': avg_order_value, 'wow_change': wow_change,
            },
            'chart_data': {
                'daily_labels': daily_labels, 'daily_revenue': daily_revenue, 'daily_profit': daily_profit,
                'top_items_labels': top_items_labels, 'top_items_revenue': top_items_revenue,
                'dow_labels': dow_order, 'dow_data': dow_data, 'hour_data': hour_data,
            },
        })
