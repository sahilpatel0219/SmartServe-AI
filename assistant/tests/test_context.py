"""
Step 6 tests: conversation follow-ups, cross-tenant isolation via context, and
per-user rate limiting. Fixtures only — no LLM, no live DB.
"""
from datetime import date
from django.test import SimpleTestCase, override_settings

from assistant import orchestrator, engine
from assistant.tools import datasource
from assistant.tests.test_tools import SALES_RECORDS, INVENTORY, CUSTOMERS, ANALYSIS

BID, OTHER = '1', '2'
TODAY = date(2024, 6, 20)


class ContextBase(SimpleTestCase):
    def setUp(self):
        import pandas as pd
        self._orig = {k: getattr(datasource, k) for k in
                      ('load_sales', 'load_inventory', 'load_customers',
                       'latest_full_analysis', 'latest_forecast', 'catalog_names', 'category_names')}
        sdf = datasource.sales_df_from_records(SALES_RECORDS)
        datasource.load_sales = lambda bid: sdf if str(bid) == BID else pd.DataFrame()
        datasource.load_inventory = lambda bid: INVENTORY if str(bid) == BID else []
        datasource.load_customers = lambda bid: CUSTOMERS if str(bid) == BID else []
        datasource.latest_full_analysis = lambda bid: ANALYSIS if str(bid) == BID else None
        datasource.latest_forecast = lambda bid: None
        datasource.catalog_names = lambda bid: ['Cold Coffee', 'Hot Coffee', 'Veg Sandwich', 'Chocolate Cake'] if str(bid) == BID else []
        datasource.category_names = lambda bid: ['Beverages', 'Desserts', 'Food'] if str(bid) == BID else []

    def tearDown(self):
        for k, v in self._orig.items():
            setattr(datasource, k, v)

    def ask(self, q, context=None, bid=BID, role='owner'):
        return orchestrator.answer(q, bid, role, 'Cafe', user_id=7, today=TODAY, context=context)


class FollowupTests(ContextBase):
    def test_multi_turn_followups(self):
        t1 = self.ask("what's my revenue this month")
        self.assertIn('₹1,270', t1['reply'])
        ctx1 = [{'q': 'rev this month', 'intent': t1['intent'], 'ent': t1['_ent']}]

        # "what about last week?" inherits metric=revenue, overlays the new window
        t2 = self.ask('what about last week?', context=ctx1)
        self.assertEqual(t2['intent'], 'metric_lookup')
        self.assertIn('₹700', t2['reply'])   # last week = 300 + 400

        # "and cold coffee?" inherits window (last week) + metric, overlays the item
        ctx2 = [{'q': 'last week', 'intent': t2['intent'], 'ent': t2['_ent']}]
        t3 = self.ask('and cold coffee?', context=ctx2)
        self.assertIn('₹400', t3['reply'])   # Cold Coffee in last week = 400 (15 Jun)
        self.assertIn('Cold Coffee', t3['reply'])

        # "why?" switches to diagnostic on the inherited window
        ctx3 = [{'q': 'cold coffee last week', 'intent': t3['intent'], 'ent': t3['_ent']}]
        t4 = self.ask('why?', context=ctx3)
        self.assertEqual(t4['intent'], 'diagnostic')

    def test_followup_without_context_is_treated_fresh(self):
        # No context → "why?" can't inherit; it should not crash and stays honest.
        r = self.ask('why?')
        self.assertIn(r['intent'], ('diagnostic', 'unclear'))


class CrossTenantContextTests(ContextBase):
    def test_context_from_other_business_never_leaks_data(self):
        # A follow-up carrying business 1's entities, but the session is business 2:
        # tools still scope to business 2 (which has no data).
        ctx1 = [{'q': 'rev', 'intent': 'metric_lookup',
                 'ent': {'metric': 'revenue', 'item': None, 'category': None, 'segment': None,
                         'time_range': {'start': '2024-06-01', 'end': '2024-06-30', 'label': 'Jun'}}}]
        r = self.ask('what about last week?', context=ctx1, bid=OTHER)
        self.assertNotIn('₹1,270', r['reply'])
        self.assertNotIn('₹700', r['reply'])
        self.assertFalse(r['ok'])


@override_settings(LLM_PROVIDER='', LLM_API_KEY='')  # force fallback, no LLM import
class RateLimitTests(ContextBase):
    def setUp(self):
        super().setUp()
        from django.core.cache import cache
        cache.clear()
        self._rl = engine.RATE_LIMIT_PER_MIN
        engine.RATE_LIMIT_PER_MIN = 2

    def tearDown(self):
        engine.RATE_LIMIT_PER_MIN = self._rl
        from django.core.cache import cache
        cache.clear()
        super().tearDown()

    def test_rate_limited_after_threshold(self):
        r1 = engine.respond('hi', BID, 'owner', 'Cafe', user_id=99)
        r2 = engine.respond('hello', BID, 'owner', 'Cafe', user_id=99)
        r3 = engine.respond('hey there', BID, 'owner', 'Cafe', user_id=99)
        self.assertTrue(r1['ok'])
        self.assertEqual(r3['intent'], 'rate_limited')
        self.assertFalse(r3['ok'])
