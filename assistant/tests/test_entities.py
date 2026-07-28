"""Entity extraction: metrics, fuzzy items, relative date phrases. DB-free."""
from datetime import date
from django.test import SimpleTestCase

from assistant import entities

# Fixed reference date: Thursday 20 June 2024 (Monday of that week = 17 June).
TODAY = date(2024, 6, 20)
CATALOG = ['Cold Coffee', 'Hot Coffee', 'Cappuccino', 'Veg Sandwich', 'Chocolate Cake']


class MetricTests(SimpleTestCase):
    def test_metrics(self):
        cases = {
            'how much revenue last week': 'revenue',
            'how many orders yesterday': 'orders',
            'what was my profit this month': 'profit',
            "what's my margin": 'margin',
            'how much am I wasting': 'waste',
            'total units sold': 'quantity',
        }
        for q, expected in cases.items():
            self.assertEqual(entities.extract_metric(q), expected, q)

    def test_profit_beats_revenue(self):
        # profit is more specific than the generic revenue words
        self.assertEqual(entities.extract_metric('profit on sales'), 'profit')


class ItemMatchTests(SimpleTestCase):
    def test_variants_resolve_to_cold_coffee(self):
        for q in ['how is cold coffee selling', 'Cold Coffee', 'iced coffee', 'coffee cold sales']:
            r = entities.match_item(q, CATALOG)
            self.assertEqual(r['match'], 'Cold Coffee', q)

    def test_typo_resolves(self):
        r = entities.match_item('how is capuccino doing', CATALOG)
        self.assertEqual(r['match'], 'Cappuccino')

    def test_ambiguous_bare_coffee(self):
        r = entities.match_item('how is coffee selling', CATALOG)
        self.assertIsNone(r['match'])
        self.assertTrue(r['ambiguous'])
        self.assertIn('Cold Coffee', r['candidates'])
        self.assertIn('Hot Coffee', r['candidates'])

    def test_no_match(self):
        r = entities.match_item('how are pizzas doing', CATALOG)
        self.assertIsNone(r['match'])

    def test_empty_catalog(self):
        r = entities.match_item('cold coffee', [])
        self.assertIsNone(r['match'])


class TimeRangeTests(SimpleTestCase):
    def _r(self, q):
        return entities.resolve_time_range(q, today=TODAY)

    def test_today_yesterday(self):
        self.assertEqual((self._r('sales today')['start'], self._r('sales today')['end']),
                         (date(2024, 6, 20), date(2024, 6, 20)))
        self.assertEqual((self._r('orders yesterday')['start'], self._r('orders yesterday')['end']),
                         (date(2024, 6, 19), date(2024, 6, 19)))

    def test_weeks(self):
        self.assertEqual((self._r('this week')['start'], self._r('this week')['end']),
                         (date(2024, 6, 17), date(2024, 6, 20)))
        self.assertEqual((self._r('last week')['start'], self._r('last week')['end']),
                         (date(2024, 6, 10), date(2024, 6, 16)))

    def test_past_n_days(self):
        r = self._r('past 7 days')
        self.assertEqual((r['start'], r['end']), (date(2024, 6, 14), date(2024, 6, 20)))
        r = self._r('last 30 days')
        self.assertEqual((r['start'], r['end']), (date(2024, 5, 22), date(2024, 6, 20)))

    def test_months(self):
        self.assertEqual((self._r('this month')['start'], self._r('this month')['end']),
                         (date(2024, 6, 1), date(2024, 6, 20)))
        self.assertEqual((self._r('last month')['start'], self._r('last month')['end']),
                         (date(2024, 5, 1), date(2024, 5, 31)))

    def test_weekend(self):
        self.assertEqual((self._r('last weekend')['start'], self._r('last weekend')['end']),
                         (date(2024, 6, 15), date(2024, 6, 16)))

    def test_quarter(self):
        self.assertEqual((self._r('this quarter')['start'], self._r('this quarter')['end']),
                         (date(2024, 4, 1), date(2024, 6, 20)))
        self.assertEqual((self._r('last quarter')['start'], self._r('last quarter')['end']),
                         (date(2024, 1, 1), date(2024, 3, 31)))

    def test_year(self):
        self.assertEqual((self._r('this year')['start'], self._r('this year')['end']),
                         (date(2024, 1, 1), date(2024, 6, 20)))
        self.assertEqual((self._r('last year')['start'], self._r('last year')['end']),
                         (date(2023, 1, 1), date(2023, 12, 31)))

    def test_since_and_in_month(self):
        self.assertEqual((self._r('since April')['start'], self._r('since April')['end']),
                         (date(2024, 4, 1), date(2024, 6, 20)))
        # "since December" with today in June resolves to last December
        self.assertEqual(self._r('since December')['start'], date(2023, 12, 1))
        self.assertEqual((self._r('in March')['start'], self._r('in March')['end']),
                         (date(2024, 3, 1), date(2024, 3, 31)))

    def test_no_time_returns_none(self):
        self.assertIsNone(self._r('what are my best sellers'))

    def test_default_window(self):
        w = entities.default_window(TODAY, days=7)
        self.assertEqual((w['start'], w['end']), (date(2024, 6, 14), date(2024, 6, 20)))


class OtherEntityTests(SimpleTestCase):
    def test_segment(self):
        self.assertEqual(entities.extract_segment('who are my VIP customers'), 'VIP')
        self.assertEqual(entities.extract_segment('how many repeat customers'), 'Regular')
        self.assertEqual(entities.extract_segment('lapsed customers'), 'Inactive')

    def test_category(self):
        cats = ['Beverages', 'Desserts']
        self.assertEqual(entities.extract_category('how are beverages doing', cats), 'Beverages')
        self.assertIsNone(entities.extract_category('how are mains doing', cats))

    def test_comparison(self):
        self.assertTrue(entities.extract_comparison('this month vs last month'))
        self.assertTrue(entities.extract_comparison('is pizza better than pasta'))
        self.assertFalse(entities.extract_comparison('how much revenue'))
