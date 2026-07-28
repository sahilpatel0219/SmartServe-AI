"""Intent classification over ~40 paraphrased questions. DB-free."""
from django.test import SimpleTestCase

from assistant import intents


# (question, expected primary intent)
CASES = [
    # metric_lookup
    ('how much did we make last week', 'metric_lookup'),
    ('how many orders yesterday', 'metric_lookup'),
    ("what's my total revenue", 'metric_lookup'),
    ('average order value', 'metric_lookup'),
    ('what were sales on Friday', 'metric_lookup'),
    # comparison
    ('is this month better than last month', 'comparison'),
    ('weekdays vs weekends', 'comparison'),
    ('compare pizza and pasta sales', 'comparison'),
    ('how does this week compare to last week', 'comparison'),
    # ranking
    ('what are my best sellers', 'ranking'),
    ('what are my top items', 'ranking'),
    ('worst performing items', 'ranking'),
    ('most popular dish', 'ranking'),
    ('least popular items', 'ranking'),
    # trend
    ('are cold drinks growing', 'trend'),
    ('how have sales moved since April', 'trend'),
    ('is coffee declining', 'trend'),
    ('sales trend over the last month', 'trend'),
    # diagnostic
    ('why were sales low yesterday', 'diagnostic'),
    ('why did profit drop', 'diagnostic'),
    ('what caused the drop in sales', 'diagnostic'),
    ('why were pizza sales down last week', 'diagnostic'),
    # forecast
    ('what will sell this weekend', 'forecast'),
    ('how much will we make tomorrow', 'forecast'),
    ("predict next week's sales", 'forecast'),
    ("what's the sales forecast", 'forecast'),
    # inventory
    ('what should I reorder', 'inventory'),
    ("what's running out", 'inventory'),
    ('what expires soon', 'inventory'),
    ('check my stock levels', 'inventory'),
    # profitability
    ('which items make the most money', 'profitability'),
    ('should I raise any prices', 'profitability'),
    ("what's my best margin item", 'profitability'),
    # waste
    ('how much am I wasting', 'waste'),
    ('what will expire before it sells', 'waste'),
    ('how much food am I throwing away', 'waste'),
    # customer
    ('who are my regulars', 'customer'),
    ('how many repeat customers', 'customer'),
    ('who are my top spenders', 'customer'),
    # staffing
    ('when am I busiest', 'staffing'),
    ('when do I need more staff', 'staffing'),
    ('what are my peak hours', 'staffing'),
    # recommendation
    ('what should I do to improve profit', 'recommendation'),
    ('how can I improve my sales', 'recommendation'),
    ('any tips to grow my business', 'recommendation'),
    # explanation
    ('what is the health score', 'explanation'),
    ('what does margin mean', 'explanation'),
    # greeting
    ('hi', 'greeting'),
    ('thanks', 'greeting'),
    ('what can you do', 'greeting'),
    # out of scope
    ('give me a pasta recipe', 'out_of_scope'),
    ("what's the weather today", 'out_of_scope'),
    ('how do I cook rice', 'out_of_scope'),
    # unclear
    ('asdf qwerty', 'unclear'),
    ('blah', 'unclear'),
]


class IntentClassificationTests(SimpleTestCase):
    def test_all_cases(self):
        failures = []
        for q, expected in CASES:
            got = intents.classify(q)['primary']
            if got != expected:
                failures.append(f'{q!r}: expected {expected}, got {got}')
        self.assertEqual(failures, [], '\n' + '\n'.join(failures))

    def test_combined_intents_surface_multiple(self):
        # "why were pizza sales down last week" is diagnostic + a metric lookup
        res = intents.classify('why were pizza sales down last week')
        self.assertEqual(res['primary'], 'diagnostic')
        self.assertIn('metric_lookup', res['all'])

    def test_coverage_at_least_40(self):
        self.assertGreaterEqual(len(CASES), 40)
