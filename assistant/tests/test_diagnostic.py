"""Diagnostic composite (explain_sales_change) + forecast confidence. Fixtures."""
from datetime import date
from django.test import SimpleTestCase

from assistant.tools import datasource, functions as fn
from assistant.tests.test_tools import SALES_RECORDS, ANALYSIS


class DiagnosticBase(SimpleTestCase):
    def setUp(self):
        import pandas as pd
        self._orig = {k: getattr(datasource, k) for k in ('load_sales', 'latest_full_analysis', 'latest_forecast')}
        sdf = datasource.sales_df_from_records(SALES_RECORDS)
        datasource.load_sales = lambda bid: sdf
        datasource.latest_full_analysis = lambda bid: ANALYSIS
        datasource.latest_forecast = lambda bid: None

    def tearDown(self):
        for k, v in self._orig.items():
            setattr(datasource, k, v)


class ExplainSalesChangeTests(DiagnosticBase):
    def test_two_period_decomposition(self):
        # A = 3rd–9th (Hot Coffee 150), B = 1st–2nd (Cold 300 + Veg 120 = 420)
        r = fn.explain_sales_change('1', 'owner',
                                    (date(2024, 6, 3), date(2024, 6, 9)),
                                    (date(2024, 6, 1), date(2024, 6, 2)))
        self.assertEqual(r['a_total'], 150.0)
        self.assertEqual(r['base_total'], 420.0)
        self.assertEqual(r['delta'], -270.0)
        self.assertEqual(r['pct_change'], -64.3)
        self.assertEqual(r['direction'], 'down')
        drops = {x['item']: x['delta'] for x in r['top_drops']}
        self.assertEqual(drops['Cold Coffee'], -300.0)   # biggest drop
        self.assertEqual(drops['Veg Sandwich'], -120.0)
        gains = {x['item']: x['delta'] for x in r['top_gains']}
        self.assertEqual(gains['Hot Coffee'], 150.0)
        # order-count context
        self.assertEqual(r['a_orders'], 1)
        self.assertEqual(r['base_orders'], 2)
        # untracked factors always surfaced, never invented as causes
        self.assertIn('weather', r['untracked'])

    def test_single_day_weekday_average_baseline(self):
        # 15 Jun is a Saturday; the only prior Saturday with data is 1 Jun (320).
        r = fn.explain_sales_change('1', 'owner', (date(2024, 6, 15), date(2024, 6, 15)))
        self.assertEqual(r['baseline_kind'], 'weekday_avg')
        self.assertEqual(r['a_total'], 400.0)
        self.assertEqual(r['base_total'], 320.0)   # avg of prior Saturdays
        self.assertEqual(r['direction'], 'up')

    def test_no_history_for_weekday(self):
        # 1 Jun is the first Saturday — nothing earlier to compare to.
        r = fn.explain_sales_change('1', 'owner', (date(2024, 6, 1), date(2024, 6, 1)))
        self.assertFalse(r['data_sufficient'])


class ForecastConfidenceTests(DiagnosticBase):
    def test_confidence_from_history(self):
        r = fn.get_forecast('1')
        self.assertEqual(r['total'], 8000)
        conf = r['confidence']
        self.assertEqual(conf['label'], 'moderate')      # 45 days of history
        self.assertEqual(conf['history_days'], 45)
        self.assertIn('not a validated error rate', conf['note'])

    def test_low_confidence_short_history(self):
        datasource.latest_full_analysis = lambda bid: {'forecast': {'total_forecast': 500, 'training_rows': 12}}
        conf = fn.get_forecast('1')['confidence']
        self.assertEqual(conf['label'], 'low')

    def test_measured_error_used_when_present(self):
        datasource.latest_full_analysis = lambda bid: {'forecast': {'total_forecast': 500, 'training_rows': 200, 'error': 8.2}}
        conf = fn.get_forecast('1')['confidence']
        self.assertEqual(conf['label'], 'measured')
        self.assertEqual(conf['error'], 8.2)
