from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from mongo import collections as col
from .tenancy import require_business


def _strip_ids(doc):
    if doc and '_id' in doc:
        doc['_id'] = str(doc['_id'])
    return doc


class MLStatusView(APIView):
    """Data readiness + latest prediction/insights summary."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        business, _ = require_business(request)
        bid = business.mongo_id
        sales_count = col.sales_records().count_documents({'business_id': bid})
        predictions = list(col.predictions().find({'business_id': bid}, sort=[('created_at', -1)], limit=1))
        latest = _strip_ids(predictions[0]) if predictions else None
        insights = [_strip_ids(i) for i in col.insights().find({'business_id': bid}, sort=[('created_at', -1)], limit=5)]
        return Response({
            'sales_count': sales_count,
            'has_enough': sales_count >= 30,
            'latest': latest,
            'insights': insights,
        })


class RunAnalysisView(APIView):
    """Synchronously runs the full ML pipeline (forecast, profitability, waste, health score)."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        business, _ = require_business(request)
        bid = business.mongo_id
        sales_count = col.sales_records().count_documents({'business_id': bid})
        if sales_count < 30:
            return Response({
                'error': f'AI analysis requires at least 30 sales records. You have {sales_count}. Upload more data first.',
            }, status=status.HTTP_400_BAD_REQUEST)

        from ml_engine.services.pipeline import run_full_analysis
        try:
            run_full_analysis(bid)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': f'Analysis failed: {e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response({'ok': True})


class MLResultsView(APIView):
    """Unpacked forecast/profitability/health/waste from the latest prediction doc."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        business, _ = require_business(request)
        bid = business.mongo_id
        predictions = list(col.predictions().find({'business_id': bid}, sort=[('created_at', -1)], limit=1))
        if not predictions:
            return Response({'error': 'No analysis results yet. Run the analysis first.'}, status=status.HTTP_404_NOT_FOUND)

        latest = _strip_ids(predictions[0])
        insights = [_strip_ids(i) for i in col.insights().find({'business_id': bid}, sort=[('created_at', -1)])]

        forecast = latest.get('forecast', {}) or {}
        daily = forecast.get('daily_forecast', []) if isinstance(forecast, dict) else []
        forecast_dates = [d['date'] for d in daily]
        forecast_values = [round(float(d['predicted_revenue']), 2) for d in daily]

        profitability = latest.get('profitability', {}) or {}
        menu_matrix = profitability.get('menu_matrix', {}) or {}
        waste = latest.get('waste', {}) or {}

        return Response({
            'latest': latest,
            'insights': insights,
            'forecast_dates': forecast_dates,
            'forecast_values': forecast_values,
            'profitability': profitability,
            'stars': menu_matrix.get('Stars', []),
            'plowhorses': menu_matrix.get('Plowhorses', []),
            'puzzles': menu_matrix.get('Puzzles', []),
            'dogs': menu_matrix.get('Dogs', []),
            'health': latest.get('health_score', {}),
            'waste_items': waste.get('high_waste_items', [])[:5],
        })


class MLInsightsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        business, _ = require_business(request)
        bid = business.mongo_id
        insights = [_strip_ids(i) for i in col.insights().find({'business_id': bid}, sort=[('created_at', -1)])]
        if not insights:
            return Response({'has_insights': False, 'insights': [], 'by_category': {}})

        by_cat = {}
        for ins in insights:
            cat = ins.get('category', 'General')
            by_cat.setdefault(cat, []).append(ins)

        return Response({'has_insights': True, 'insights': insights, 'by_category': by_cat})
