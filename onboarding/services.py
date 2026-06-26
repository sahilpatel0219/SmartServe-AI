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
    'customers': {
        'required': ['name'],
        'optional': ['phone', 'email', 'visit_count', 'total_spend', 'notes'],
        'date_cols': [],
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
    'customers': {
        'name':        ['name', 'customer_name', 'customer', 'full_name', 'client'],
        'phone':       ['phone', 'mobile', 'contact', 'phone_number', 'contact_number'],
        'email':       ['email', 'email_address', 'mail'],
        'visit_count': ['visit_count', 'visits', 'orders', 'order_count', 'no_of_visits'],
        'total_spend': ['total_spend', 'total_spent', 'spend', 'lifetime_value', 'ltv', 'amount'],
        'notes':       ['notes', 'remarks', 'comments'],
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
    'customers': [
        {'name': 'Riya Shah', 'phone': '9876543210', 'email': 'riya@example.com', 'visit_count': 12, 'total_spend': 4800, 'notes': 'Prefers oat milk'},
        {'name': 'Aman Verma', 'phone': '9876500011', 'email': 'aman@example.com', 'visit_count': 3, 'total_spend': 900, 'notes': ''},
    ],
}


# ── Numeric helpers ──────────────────────────────────────────────────────────
def _to_num(val, default=0.0):
    """Best-effort convert a CSV string to a float; returns default on failure."""
    if val is None:
        return default
    try:
        s = str(val).replace(',', '').strip()
        return float(s) if s != '' else default
    except (ValueError, TypeError):
        return default


def normalize_records(records: list, upload_type: str) -> list:
    """
    Convert raw CSV rows (all strings) into the app's canonical internal schema:
    numeric fields become numbers, field names match what the views/templates use,
    and order line-items are grouped into one document per order.
    """
    if upload_type == 'sales':
        out = []
        for r in records:
            out.append({
                'date':      str(r.get('date', '')).strip()[:10],
                'item_name': str(r.get('item_name', '')).strip(),
                'quantity':  _to_num(r.get('quantity')),
                'revenue':   _to_num(r.get('revenue')),
                'cost':      _to_num(r.get('cost')),
                'category':  str(r.get('category', '')).strip(),
            })
        return out

    if upload_type == 'inventory':
        out = []
        for r in records:
            out.append({
                'item_name':     str(r.get('item_name', '')).strip(),
                'quantity':      _to_num(r.get('quantity')),
                'unit':          str(r.get('unit', '')).strip(),
                'cost_per_unit': _to_num(r.get('cost_per_unit')),
                'reorder_level': _to_num(r.get('reorder_level')),
                'expiry_date':   str(r.get('expiry_date', '')).strip() or None,
                'category':      str(r.get('category', '')).strip(),
                'supplier':      str(r.get('supplier', '')).strip(),
            })
        return out

    if upload_type == 'menu':
        out = []
        for r in records:
            avail = str(r.get('is_available', 'yes')).strip().lower()
            out.append({
                'name':         str(r.get('item_name', '')).strip(),
                'category':     str(r.get('category', '')).strip(),
                'price':        _to_num(r.get('price')),
                'cost':         _to_num(r.get('cost')),
                'description':  str(r.get('description', '')).strip(),
                'is_available': avail in ('yes', 'true', '1', 'available', 'y', ''),
                'recipe':       [],
            })
        return out

    if upload_type == 'orders':
        # Group flat line-item rows into one document per order_id
        groups, seq = {}, []
        for i, r in enumerate(records):
            oid = str(r.get('order_id', '')).strip() or f'AUTO{i}'
            if oid not in groups:
                groups[oid] = {
                    'order_id':      oid,
                    'order_type':    str(r.get('order_type', '')).strip() or 'dine_in',
                    'customer_name': str(r.get('customer_name', '')).strip(),
                    'items':         [],
                    'total_amount':  0.0,
                    'status':        str(r.get('status', '')).strip().lower() or 'delivered',
                    'order_date':    str(r.get('order_date', '')).strip()[:10],
                }
                seq.append(oid)
            qty = _to_num(r.get('quantity'), 1) or 1
            amt = _to_num(r.get('amount'))
            groups[oid]['items'].append({
                'name':     str(r.get('item_name', '')).strip(),
                'quantity': qty,
                'subtotal': amt,
                'price':    round(amt / qty, 2) if qty else amt,
            })
            groups[oid]['total_amount'] += amt

        out = []
        for oid in seq:
            g = groups[oid]
            try:
                g['created_at'] = pd.to_datetime(g['order_date']).to_pydatetime().replace(tzinfo=timezone.utc)
            except Exception:
                g['created_at'] = datetime.now(timezone.utc)
            out.append(g)
        return out

    if upload_type == 'customers':
        out = []
        for r in records:
            name = str(r.get('name', '')).strip()
            if not name:
                continue
            out.append({
                'name':        name,
                'phone':       str(r.get('phone', '')).strip(),
                'email':       str(r.get('email', '')).strip(),
                'visit_count': int(_to_num(r.get('visit_count'))),
                'total_spend': _to_num(r.get('total_spend')),
                'notes':       str(r.get('notes', '')).strip(),
            })
        return out

    return records


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
        'customers': col.customers,
    }[upload_type]()

    # Convert raw rows into the app's canonical schema (numbers, field names, grouping)
    docs = normalize_records(records, upload_type)

    # Tag and insert
    for d in docs:
        d['business_id'] = business_id
        d['_source'] = 'upload'
        d.setdefault('created_at', now)  # orders keep their derived date

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
