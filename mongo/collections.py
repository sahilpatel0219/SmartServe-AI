"""
Named accessors for every MongoDB collection.
Import these instead of hard-coding collection names anywhere else.
All collections carry a `business_id` field for multi-tenant isolation.
"""
from .client import get_db


def uploaded_datasets():
    return get_db()['uploaded_datasets']

def sales_records():
    return get_db()['sales_records']

def menu_items():
    return get_db()['menu_items']

def ingredients():
    return get_db()['ingredients']

def inventory():
    return get_db()['inventory']

def orders():
    return get_db()['orders']

def customers():
    return get_db()['customers']

def employees():
    return get_db()['employees']

def attendance():
    return get_db()['attendance']

def suppliers():
    return get_db()['suppliers']

def purchase_orders():
    return get_db()['purchase_orders']

def predictions():
    return get_db()['predictions']

def insights():
    return get_db()['insights']

def recommendations():
    return get_db()['recommendations']

def notifications():
    return get_db()['notifications']

def reports():
    return get_db()['reports']

def audit_logs():
    return get_db()['audit_logs']
