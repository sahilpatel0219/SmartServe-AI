"""
Upload validation, preview, and commit service.
Handles CSV and XLSX files; enforces required columns per upload type.
"""
import io
import csv
from datetime import datetime, timezone

import pandas as pd
from django.http import HttpResponse
from mongo import collections as col


# ── Required columns per upload type ─────────────────────────────────────────
SCHEMA = {
    'sales': {
        'required': ['date', 'item_name', 'quantity', 'revenue'],
        'optional': ['cost', 'category', 'order_type'],
        'date_cols': ['date'],
    },
    'inventory': {
        'required': ['item_name', 'quantity', 'unit', 'cost_per_unit', 'reorder_level'],
        'optional': ['expiry_date', 'category', 'supplier'],
        'date_cols': ['expiry_date'],
    },
    'menu': {
        'required': ['item_name', 'category', 'price'],
        'optional': ['cost', 'is_available', 'description'],
        'date_cols': [],
    },
    'orders': {
        'required': ['order_date', 'order_id', 'item_name', 'quantity', 'amount'],
        'optional': ['order_type', 'customer_name', 'status'],
        'date_cols': ['order_date'],
    },
}

# ── Column aliases per type ──────────────────────────────────────────────────
# Maps each canonical column → list of accepted source names (after normalisation).
# Lets users upload real-world files with varied headers (Item, Product, Qty, …)
# without renaming columns by hand.
COLUMN_ALIASES = {
    'sales': {
        'date':      ['date', 'sale_date', 'transaction_date', 'day', 'order_date', 'datetime'],
        'item_name': ['item_name', 'item', 'product', 'product_name', 'name', 'dish', 'menu_item'],
        'quantity':  ['quantity', 'qty', 'units', 'count', 'qty_sold', 'units_sold', 'no_of_items'],
        'revenue':   ['revenue', 'sales', 'sales_amount', 'amount', 'total', 'total_amount', 'total_revenue'],
        'cost':      ['cost', 'cost_price', 'cogs', 'total_cost'],
        'category':  ['category', 'group', 'section'],
        'order_type':['order_type', 'source', 'channel'],
    },
    'inventory': {
        'item_name':     ['item_name', 'item', 'ingredient', 'product', 'name', 'material'],
        'quantity':      ['quantity', 'qty', 'stock', 'current_stock', 'on_hand', 'in_stock'],
        'unit':          ['unit', 'uom', 'measure', 'units'],
        'cost_per_unit': ['cost_per_unit', 'unit_cost', 'price_per_unit', 'rate', 'cost'],
        'reorder_level': ['reorder_level', 'min_threshold', 'minimum', 'threshold', 'min_stock', 'reorder', 'reorder_point', 'min_qty'],
        'expiry_date':   ['expiry_date', 'expiry', 'expiration', 'best_before', 'use_by'],
        'category':      ['category', 'group', 'type'],
        'supplier':      ['supplier', 'vendor'],
    },
    'menu': {
        'item_name':    ['item_name', 'item', 'product', 'name', 'dish', 'menu_item'],
        'category':     ['category', 'group', 'section', 'type'],
        'price':        ['price', 'selling_price', 'mrp', 'rate', 'amount'],
        'cost':         ['cost', 'cost_price', 'cogs'],
        'is_available': ['is_available', 'available', 'active'],
        'description':  ['description', 'desc', 'details'],
    },
    'orders': {
        'order_date':    ['order_date', 'date', 'sale_date', 'transaction_date', 'datetime'],
        'order_id':      ['order_id', 'order_no', 'bill_no', 'invoice', 'invoice_no', 'receipt_no', 'id'],
        'item_name':     ['item_name', 'item', 'product', 'name', 'dish'],
        'quantity':      ['quantity', 'qty', 'units', 'count', 'item_count'],
        'amount':        ['amount', 'total', 'total_amount', 'bill_amount', 'revenue'],
        'order_type':    ['order_type', 'source', 'channel', 'type'],
        'customer_name': ['customer_name', 'customer', 'client', 'guest'],
        'status':        ['status', 'state'],
    },
}


def _apply_aliases(df, upload_type):
    """Rename any recognised alias columns to their canonical names (in place)."""
    aliases = COLUMN_ALIASES.get(upload_type, {})
    present = set(df.columns)
    rename_map = {}
    for canonical, variants in aliases.items():
        if canonical in present:
            continue  # already correctly named
        for v in variants:
            if v in present and v not in rename_map.values():
                rename_map[v] = canonical
                break
    if rename_map:
        df.rename(columns=rename_map, inplace=True)
    return df


TEMPLATE_ROWS = {
    'sales': [
        {'date': '2024-01-01', 'item_name': 'Masala Dosa', 'quantity': 5, 'revenue': 600, 'cost': 200},
        {'date': '2024-01-01', 'item_name': 'Filter Coffee', 'quantity': 10, 'revenue': 300, 'cost': 80},
    ],
    'inventory': [
        {'item_name': 'Rice', 'quantity': 25, 'unit': 'kg', 'cost_per_unit': 45, 'reorder_level': 5, 'expiry_date': ''},
        {'item_name': 'Milk', 'quantity': 10, 'unit': 'litre', 'cost_per_unit': 65, 'reorder_level': 2, 'expiry_date': '2024-02-10'},
    ],
    'menu': [
        {'item_name': 'Masala Dosa', 'category': 'Breakfast', 'price': 120, 'cost': 40, 'is_available': 'yes'},
        {'item_name': 'Filter Coffee', 'category': 'Beverages', 'price': 30, 'cost': 8, 'is_available': 'yes'},
    ],
    'orders': [
        {'order_date': '2024-01-01', 'order_id': 'ORD001', 'item_name': 'Masala Dosa', 'quantity': 2, 'amount': 240, 'order_type': 'dine_in'},
        {'order_date': '2024-01-01', 'order_id': 'ORD001', 'item_name': 'Filter Coffee', 'quantity': 2, 'amount': 60, 'order_type': 'dine_in'},
    ],
}


def validate_and_preview(uploaded_file, upload_type: str) -> dict:
    """
    Parse the uploaded CSV/XLSX, validate columns and data types,
    return a structured result with preview rows and any row-level errors.
    """
    schema = SCHEMA.get(upload_type)
    if not schema:
        return {'status': 'error', 'message': f'Unknown upload type: {upload_type}'}

    filename = uploaded_file.name.lower()
    try:
        if filename.endswith('.csv'):
            df = pd.read_csv(uploaded_file, dtype=str)
        elif filename.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(uploaded_file, dtype=str)
        else:
            return {'status': 'error', 'message': 'Only CSV and XLSX files are supported.'}
    except Exception as e:
        return {'status': 'error', 'message': f'Could not read file: {e}'}

    if df.empty:
        return {'status': 'error', 'message': 'The file is empty.'}

    # Normalise column names: lowercase, strip whitespace, replace spaces/hyphens with underscores
    df.columns = [c.strip().lower().replace(' ', '_').replace('-', '_') for c in df.columns]

    # Auto-map common alternative headers (Item → item_name, Qty → quantity, …)
    df = _apply_aliases(df, upload_type)

    # Check required columns
    missing = [c for c in schema['required'] if c not in df.columns]
    if missing:
        found = ', '.join(df.columns) or '(none)'
        return {
            'status': 'error',
            'message': f'Missing required column(s): {", ".join(missing)}. '
                       f'Your file has these columns: {found}. '
                       f'Rename them to match, or download the template for the exact format.'
        }

    # Remove completely empty rows
    df = df.dropna(how='all')

    # Validate date columns
    row_errors = []
    for date_col in schema['date_cols']:
        if date_col in df.columns:
            for idx, val in df[date_col].items():
                if pd.isna(val) or str(val).strip() == '':
                    continue  # optional or blank allowed
                try:
                    pd.to_datetime(str(val))
                except Exception:
                    row_errors.append(f'Row {idx + 2}: "{date_col}" value "{val}" is not a valid date.')

    # Validate numeric columns for sales/inventory/orders/menu
    numeric_hints = {
        'sales': ['quantity', 'revenue', 'cost'],
        'inventory': ['quantity', 'cost_per_unit', 'reorder_level'],
        'menu': ['price', 'cost'],
        'orders': ['quantity', 'amount'],
    }
    for col_name in numeric_hints.get(upload_type, []):
        if col_name in df.columns:
            for idx, val in df[col_name].items():
                if pd.isna(val) or str(val).strip() == '':
                    continue
                try:
                    float(str(val).replace(',', ''))
                except ValueError:
                    row_errors.append(f'Row {idx + 2}: "{col_name}" value "{val}" must be a number.')

    # Build clean records (dicts, for MongoDB insertion)
    records = df.to_dict(orient='records')

    # Preview columns — only those present in the file
    preview_cols = schema['required'] + [c for c in schema.get('optional', []) if c in df.columns]
    # Preview rows as list-of-lists so Django templates can iterate without dynamic key lookups
    preview_rows_matrix = [
        [str(row.get(c, '')) for c in preview_cols]
        for row in records[:10]
    ]

    return {
        'status': 'ok',
        'row_count': len(records),
        'records': records,
        'preview_rows': preview_rows_matrix,
        'preview_cols': preview_cols,
        'columns': list(df.columns),
        'row_errors': row_errors[:20],  # cap at 20 shown errors
        'has_errors': len(row_errors) > 0,
        'upload_type': upload_type,
        'filename': uploaded_file.name,
    }


def commit_upload(records: list, upload_type: str, business_id: str,
                  filename: str, row_count: int):
    """
    Persist validated records into MongoDB.
    Registers the upload in uploaded_datasets and inserts the records
    into the appropriate collection.
    """
    now = datetime.now(timezone.utc)

    # Register dataset record
    col.uploaded_datasets().insert_one({
        'business_id': business_id,
        'type': upload_type,
        'filename': filename,
        'row_count': row_count,
        'status': 'active',
        'uploaded_at': now,
    })

    # Map upload type → target collection
    target = {
        'sales': col.sales_records,
        'inventory': col.inventory,
        'menu': col.menu_items,
        'orders': col.orders,
    }[upload_type]()

    # Tag and insert
    docs = []
    for r in records:
        r['business_id'] = business_id
        r['_source'] = 'upload'
        r['created_at'] = now
        docs.append(r)

    if docs:
        target.insert_many(docs)


def generate_template_csv(upload_type: str) -> HttpResponse:
    """Return a downloadable CSV template for the given upload type."""
    rows = TEMPLATE_ROWS.get(upload_type)
    if not rows:
        return HttpResponse('Invalid template type', status=400)

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

    response = HttpResponse(output.getvalue(), content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="smartserve_{upload_type}_template.csv"'
    return response
