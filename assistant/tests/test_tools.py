"""
Tool registry unit tests — exact numbers against fixed fixtures.

No MongoDB and no LLM: the datasource seam is monkeypatched to return in-memory
fixtures. Also proves tenant scoping (a different business_id sees no data) and
role gating (Staff denied financial tools).
"""
from datetime import date
from django.test import SimpleTestCase

from assistant.tools import datasource, functions as fn

BID = '1'          # the session's business
OTHER = '2'        # a different tenant — must see nothing

SALES_RECORDS = [
    {'date': '2024-06-01', 'item_name': 'Cold Coffee',    'category': 'Beverages', 'order_id': 'o1', 'quantity': 2, 'revenue': 200, 'cost': 80},
    {'date': '2024-06-01', 'item_name': 'Veg Sandwich',   'category': 'Food',      'order_id': 'o1', 'quantity': 1, 'revenue': 120, 'cost': 50},
    {'date': '2024-06-02', 'item_name': 'Cold Coffee',    'category': 'Beverages', 'order_id': 'o2', 'quantity': 1, 'revenue': 100, 'cost': 40},
    {'date': '2024-06-03', 'item_name': 'Hot Coffee',     'category': 'Beverages', 'order_id': 'o3', 'quantity': 3, 'revenue': 150, 'cost': 60},
    {'date': '2024-06-10', 'item_name': 'Chocolate Cake', 'category': 'Desserts',  'order_id': 'o4', 'quantity': 2, 'revenue': 300, 'cost': 120},
    {'date': '2024-06-15', 'item_name': 'Cold Coffee',    'category': 'Beverages', 'order_id': 'o5', 'quantity': 4, 'revenue': 400, 'cost': 160},
]
INVENTORY = [
    {'item_name': 'Tomatoes',     'quantity': 5,  'reorder_level': 10, 'unit': 'kg', 'expiry_date': '2024-06-05'},
    {'item_name': 'Milk',         'quantity': 20, 'reorder_level': 5,  'unit': 'L',  'expiry_date': '2024-06-03'},
    {'item_name': 'Coffee Beans', 'quantity': 2,  'reorder_level': 3,  'unit': 'kg'},
]
CUSTOMERS = [
    {'name': 'Alice', 'visit_count': 25, 'total_spend': 6000},
    {'name': 'Bob',   'visit_count': 8,  'total_spend': 2000},
    {'name': 'Carol', 'visit_count': 2,  'total_spend': 300},
]
ANALYSIS = {
    'health_score': {'total_score': 72.5, 'components': {'sales': 18, 'profit': 12, 'inventory': 20, 'growth': 22.5}},
    'waste': {'estimated_loss_inr': 1500, 'high_waste_items': [{'item': 'Milk'}]},
    'forecast': {'total_forecast': 8000, 'training_rows': 45},
}

JUN = (date(2024, 6, 1), date(2024, 6, 30))


class ToolTestBase(SimpleTestCase):
    def setUp(self):
        self._orig = {k: getattr(datasource, k) for k in
                      ('load_sales', 'load_inventory', 'load_customers',
                       'latest_full_analysis', 'latest_forecast')}
        sales_df = datasource.sales_df_from_records(SALES_RECORDS)
        import pandas as pd
        datasource.load_sales = lambda bid: sales_df if str(bid) == BID else pd.DataFrame()
        datasource.load_inventory = lambda bid: INVENTORY if str(bid) == BID else []
        datasource.load_customers = lambda bid: CUSTOMERS if str(bid) == BID else []
        datasource.latest_full_analysis = lambda bid: ANALYSIS if str(bid) == BID else None
        datasource.latest_forecast = lambda bid: None

    def tearDown(self):
        for k, v in self._orig.items():
            setattr(datasource, k, v)


class MetricTests(ToolTestBase):
    def test_totals(self):
        r = fn.get_metric(BID, 'owner', 'revenue', *JUN)
        self.assertEqual(r['value'], 1270.0)
        self.assertEqual(fn.get_metric(BID, 'owner', 'cost', *JUN)['value'], 510.0)
        self.assertEqual(fn.get_metric(BID, 'owner', 'quantity', *JUN)['value'], 13.0)
        self.assertEqual(fn.get_metric(BID, 'owner', 'profit', *JUN)['value'], 760.0)
        self.assertEqual(fn.get_metric(BID, 'owner', 'margin', *JUN)['value'], 59.8)
        self.assertEqual(fn.get_metric(BID, 'owner', 'orders', *JUN)['value'], 5)

    def test_window_and_item_filter(self):
        r = fn.get_metric(BID, 'owner', 'revenue', date(2024, 6, 1), date(2024, 6, 3))
        self.assertEqual(r['value'], 570.0)
        self.assertEqual(r['window']['label'], entities_label(date(2024, 6, 1), date(2024, 6, 3)))
        cc = fn.get_metric(BID, 'owner', 'revenue', *JUN, item='Cold Coffee')
        self.assertEqual(cc['value'], 700.0)

    def test_window_orders_distinct(self):
        r = fn.get_metric(BID, 'owner', 'orders', date(2024, 6, 1), date(2024, 6, 3))
        self.assertEqual(r['value'], 3)  # o1, o2, o3

    def test_no_sales_is_insufficient(self):
        r = fn.get_metric(OTHER, 'owner', 'revenue', *JUN)
        self.assertFalse(r['data_sufficient'])
        self.assertEqual(r['need'], 'sales')


class RoleGatingTests(ToolTestBase):
    def test_staff_denied_financial(self):
        self.assertTrue(fn.get_metric(BID, 'staff', 'profit', *JUN)['denied'])
        self.assertTrue(fn.get_metric(BID, 'staff', 'margin', *JUN)['denied'])
        self.assertTrue(fn.rank_items(BID, 'staff', 'profit', *JUN)['denied'])
        self.assertTrue(fn.get_item_profitability(BID, 'staff')['denied'])

    def test_staff_allowed_operational(self):
        self.assertFalse(fn.get_metric(BID, 'staff', 'revenue', *JUN)['denied'])
        self.assertFalse(fn.get_metric(BID, 'staff', 'orders', *JUN)['denied'])


class RankTrendTests(ToolTestBase):
    def test_rank_top_revenue(self):
        r = fn.rank_items(BID, 'owner', 'revenue', *JUN, limit=3)
        self.assertEqual([i['item'] for i in r['items']], ['Cold Coffee', 'Chocolate Cake', 'Hot Coffee'])
        self.assertEqual(r['items'][0]['value'], 700.0)

    def test_rank_bottom(self):
        r = fn.rank_items(BID, 'owner', 'revenue', *JUN, limit=1, ascending=True)
        self.assertEqual(r['items'][0]['item'], 'Veg Sandwich')
        self.assertEqual(r['items'][0]['value'], 120.0)

    def test_compare_periods(self):
        r = fn.compare_periods(BID, 'owner', 'revenue',
                               (date(2024, 6, 1), date(2024, 6, 3)),
                               (date(2024, 6, 10), date(2024, 6, 15)))
        self.assertEqual(r['period_a']['value'], 570.0)
        self.assertEqual(r['period_b']['value'], 700.0)
        self.assertEqual(r['delta'], -130.0)
        self.assertEqual(r['pct_change'], -18.6)
        self.assertEqual(r['direction'], 'down')

    def test_trend_daily(self):
        r = fn.get_trend(BID, 'owner', 'revenue', date(2024, 6, 1), date(2024, 6, 15), 'day')
        first = next(x for x in r['series'] if x['bucket'] == '2024-06-01')
        self.assertEqual(first['value'], 320.0)   # 200 + 120
        self.assertEqual(r['direction'], 'up')     # 320 → 400

    def test_breakdown_category(self):
        r = fn.get_sales_breakdown(BID, 'owner', *JUN, by='category')
        m = {x['key']: x['revenue'] for x in r['breakdown']}
        self.assertEqual(m['Beverages'], 850.0)
        self.assertEqual(m['Food'], 120.0)
        self.assertEqual(m['Desserts'], 300.0)

    def test_breakdown_weekday(self):
        r = fn.get_sales_breakdown(BID, 'owner', *JUN, by='weekday')
        m = {x['key']: x['revenue'] for x in r['breakdown']}
        self.assertEqual(m['Saturday'], 720.0)     # 06-01 (320) + 06-15 (400)
        self.assertEqual(m['Monday'], 450.0)       # 06-03 (150) + 06-10 (300)

    def test_breakdown_hour_unavailable(self):
        r = fn.get_sales_breakdown(BID, 'owner', *JUN, by='hour')
        self.assertFalse(r['data_sufficient'])


class InventoryCustomerTests(ToolTestBase):
    def test_low_stock(self):
        r = fn.get_low_stock(BID)
        names = [i['item'] for i in r['items']]
        self.assertEqual(r['count'], 2)
        self.assertEqual(names, ['Coffee Beans', 'Tomatoes'])  # sorted by qty

    def test_reorder_suggestions(self):
        r = fn.get_reorder_suggestions(BID)
        m = {i['item']: i['suggested_order'] for i in r['items']}
        self.assertEqual(m['Coffee Beans'], 4.0)   # target 6 - 2
        self.assertEqual(m['Tomatoes'], 15.0)      # target 20 - 5

    def test_expiring_soon(self):
        r = fn.get_expiring_soon(BID, days=3)
        items = [i['item'] for i in r['items']]
        self.assertEqual(r['count'], 2)
        self.assertNotIn('Coffee Beans', items)    # no expiry date

    def test_customer_stats(self):
        r = fn.get_customer_stats(BID)
        self.assertEqual(r['total'], 3)
        self.assertEqual(r['segments'], {'VIP': 1, 'Regular': 1, 'Inactive': 1})
        self.assertEqual(r['top_spenders'][0], {'name': 'Alice', 'total_spend': 6000.0})
        self.assertEqual(fn.get_customer_stats(BID, segment='VIP')['segment_count'], 1)

    def test_peak_times(self):
        r = fn.get_peak_times(BID)
        self.assertEqual(r['busiest_weekday']['weekday'], 'Saturday')
        self.assertIsNone(r['peak_hours'])         # no timestamps


class ProfitAndAiTests(ToolTestBase):
    def test_item_profitability(self):
        r = fn.get_item_profitability(BID, 'owner')
        self.assertEqual(r['items'][0]['item'], 'Cold Coffee')
        self.assertEqual(r['items'][0]['profit'], 420.0)
        self.assertEqual(r['items'][0]['margin_pct'], 60.0)

    def test_health_score(self):
        r = fn.get_health_score(BID)
        self.assertEqual(r['score'], 72.5)
        self.assertEqual(r['weakest'], 'profit')   # lowest component (12)

    def test_waste_risk(self):
        r = fn.get_waste_risk(BID)
        self.assertEqual(r['estimated_loss'], 1500)

    def test_forecast(self):
        r = fn.get_forecast(BID)
        self.assertEqual(r['total'], 8000)
        self.assertEqual(r['training_rows'], 45)
        self.assertIn('caveat', r)

    def test_data_availability(self):
        r = fn.get_data_availability(BID)
        self.assertTrue(r['has_sales'] and r['has_cost'] and r['has_analysis'])
        self.assertEqual(r['sales_rows'], 6)
        self.assertEqual(r['coverage']['days_with_data'], 5)


class TenantIsolationTests(ToolTestBase):
    def test_other_business_sees_nothing(self):
        # The exact same tools, called with a different business_id, must not
        # surface this business's data.
        self.assertFalse(fn.get_metric(OTHER, 'owner', 'revenue', *JUN)['data_sufficient'])
        self.assertFalse(fn.get_low_stock(OTHER)['data_sufficient'])
        self.assertFalse(fn.get_customer_stats(OTHER)['data_sufficient'])
        self.assertFalse(fn.get_health_score(OTHER)['data_sufficient'])


def entities_label(a, b):
    from assistant import entities
    return entities.range_label(a, b)
