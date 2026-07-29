"""
Reports module: PDF and Excel exports from real MongoDB data.
"""
import io
from datetime import datetime, timezone

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from accounts.models import Membership
from mongo import collections as col
import pandas as pd


def _get_business(request):
    from core.utils import get_active_business
    return get_active_business(request)


def _period_cutoff(period_str):
    days = int(period_str) if period_str in ['7', '30', '90', '365'] else 30
    return pd.Timestamp.now(tz='UTC') - pd.Timedelta(days=days), days


def _load_df(collection_fn, bid, date_col, rev_col):
    records = list(collection_fn().find({'business_id': bid}))
    if not records:
        return pd.DataFrame()
    df = pd.DataFrame(records)
    if date_col not in df.columns or rev_col not in df.columns:
        return pd.DataFrame()
    df['_date'] = pd.to_datetime(df[date_col], errors='coerce')
    df['_revenue'] = pd.to_numeric(df[rev_col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    return df.dropna(subset=['_date'])


@login_required
def index_view(request):
    business, _ = _get_business(request)
    if not business:
        return redirect('onboarding:create_business')
    bid = business.mongo_id

    # Check which data types are available
    has_sales = col.sales_records().count_documents({'business_id': bid}) > 0
    has_inventory = col.inventory().count_documents({'business_id': bid}) > 0
    has_customers = col.customers().count_documents({'business_id': bid}) > 0
    has_staff = col.employees().count_documents({'business_id': bid}) > 0
    has_orders = col.orders().count_documents({'business_id': bid}) > 0

    return render(request, 'reports/index.html', {
        'business': business,
        'has_sales': has_sales,
        'has_inventory': has_inventory,
        'has_customers': has_customers,
        'has_staff': has_staff,
        'has_orders': has_orders,
        'period_options': [('7', '7 days'), ('30', '30 days'), ('90', '90 days'), ('365', '1 year')],
    })


@login_required
def export_view(request, report_type, fmt):
    business, _ = _get_business(request)
    if not business:
        return redirect('onboarding:create_business')
    bid = business.mongo_id
    period = request.GET.get('period', '30')
    cutoff, days = _period_cutoff(period)

    if report_type == 'sales':
        return _export_sales(bid, fmt, cutoff, days, business.name)
    elif report_type == 'inventory':
        return _export_inventory(bid, fmt, business.name)
    elif report_type == 'customers':
        return _export_customers(bid, fmt, business.name)
    elif report_type == 'staff':
        return _export_staff(bid, fmt, business.name)
    elif report_type == 'orders':
        return _export_orders(bid, fmt, business.name)
    else:
        return HttpResponse('Invalid report type', status=400)


# ── Sales report ──────────────────────────────────────────────────────────────

def _export_sales(bid, fmt, cutoff, days, biz_name):
    records = list(col.sales_records().find({'business_id': bid}))
    if not records:
        return HttpResponse('No sales data available.', status=404)

    df = pd.DataFrame(records)
    date_col = next((c for c in ['date', 'order_date', 'Date'] if c in df.columns), None)
    rev_col = next((c for c in ['revenue', 'amount', 'Revenue'] if c in df.columns), None)
    if not date_col or not rev_col:
        return HttpResponse('Sales data format not recognized.', status=400)

    df['_date'] = pd.to_datetime(df[date_col], errors='coerce')
    df['_revenue'] = pd.to_numeric(df[rev_col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    df = df.dropna(subset=['_date'])

    if df['_date'].dt.tz is None:
        cutoff = cutoff.tz_localize(None)
    df = df[df['_date'] >= cutoff]

    # Summary table
    summary = df.groupby(df['_date'].dt.date)['_revenue'].agg(['sum', 'count']).reset_index()
    summary.columns = ['Date', 'Revenue (₹)', 'Transactions']
    summary['Revenue (₹)'] = summary['Revenue (₹)'].round(2)
    summary = summary.sort_values('Date')

    title = f'{biz_name} — Sales Report (Last {days} days)'
    filename = f'sales_report_{days}d'

    if fmt == 'excel':
        return _to_excel(summary, filename, title)
    elif fmt == 'pdf':
        return _to_pdf(summary, filename, title, ['Date', 'Revenue (₹)', 'Transactions'])
    return HttpResponse('Invalid format.', status=400)


# ── Inventory report ──────────────────────────────────────────────────────────

def _export_inventory(bid, fmt, biz_name):
    records = list(col.inventory().find({'business_id': bid}))
    if not records:
        return HttpResponse('No inventory data available.', status=404)

    df = pd.DataFrame(records)
    keep = [c for c in ['item_name', 'quantity', 'unit', 'cost_per_unit', 'reorder_level', 'expiry_date'] if c in df.columns]
    df = df[keep].copy()
    df.columns = [c.replace('_', ' ').title() for c in df.columns]

    title = f'{biz_name} — Inventory Report'
    filename = 'inventory_report'

    if fmt == 'excel':
        return _to_excel(df, filename, title)
    elif fmt == 'pdf':
        return _to_pdf(df, filename, title, list(df.columns))
    return HttpResponse('Invalid format.', status=400)


# ── Customer report ───────────────────────────────────────────────────────────

def _export_customers(bid, fmt, biz_name):
    records = list(col.customers().find({'business_id': bid}, sort=[('name', 1)]))
    return _export_columns(
        records, ['name', 'phone', 'email', 'visit_count', 'total_spend'],
        f'{biz_name} — Customer Report', 'customer_report', fmt,
        empty_msg='No customer data available.',
    )


# ── Staff report ──────────────────────────────────────────────────────────────

def _export_staff(bid, fmt, biz_name):
    records = list(col.employees().find({'business_id': bid}, sort=[('name', 1)]))
    return _export_columns(
        records, ['name', 'role', 'phone', 'email', 'salary', 'join_date', 'status'],
        f'{biz_name} — Staff Report', 'staff_report', fmt,
        empty_msg='No staff data available.',
    )


# ── Order report ──────────────────────────────────────────────────────────────

def _export_orders(bid, fmt, biz_name):
    records = list(col.orders().find({'business_id': bid}, sort=[('created_at', -1)]))
    if not records:
        return HttpResponse('No order data available.', status=404)

    rows = []
    for o in records:
        dt = o.get('created_at') or o.get('order_date')
        date_s = dt.strftime('%Y-%m-%d %H:%M') if isinstance(dt, datetime) else str(dt or '')[:16]
        items = o.get('items')
        if isinstance(items, list):
            items_s = f'{len(items)} item(s)'
        else:
            items_s = str(o.get('item_name') or items or '—')
        total = o.get('total_amount', o.get('amount', 0)) or 0
        rows.append({
            'Date': date_s,
            'Order ID': str(o.get('order_id') or o.get('_id', ''))[:12],
            'Customer': o.get('customer_name') or '—',
            'Items': items_s,
            'Total (₹)': total,
            'Type': (o.get('order_type') or '—').replace('_', ' ').title(),
            'Status': (o.get('status') or '—').title(),
        })
    df = pd.DataFrame(rows)
    title = f'{biz_name} — Orders Report'
    if fmt == 'excel':
        return _to_excel(df, 'orders_report', title)
    elif fmt == 'pdf':
        return _to_pdf(df, 'orders_report', title, list(df.columns))
    return HttpResponse('Invalid format.', status=400)


# ── Shared column exporter ────────────────────────────────────────────────────

def _export_columns(records, keep, title, filename, fmt, empty_msg='No data available.'):
    """Export a collection's records, keeping only the columns that exist."""
    if not records:
        return HttpResponse(empty_msg, status=404)
    df = pd.DataFrame(records)
    cols = [c for c in keep if c in df.columns]
    if not cols:
        return HttpResponse('Data format not recognized.', status=400)
    df = df[cols].copy()
    df.columns = [c.replace('_', ' ').title() for c in cols]
    if fmt == 'excel':
        return _to_excel(df, filename, title)
    elif fmt == 'pdf':
        return _to_pdf(df, filename, title, list(df.columns))
    return HttpResponse('Invalid format.', status=400)


# ── Exporters ─────────────────────────────────────────────────────────────────

def _to_excel(df: pd.DataFrame, filename: str, title: str) -> HttpResponse:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as writer:
        # Write title row then data
        df.to_excel(writer, index=False, startrow=2, sheet_name='Report')
        ws = writer.sheets['Report']
        ws['A1'] = title
        ws['A1'].font = __import__('openpyxl').styles.Font(bold=True, size=13)
        # Auto-width columns
        for col_cells in ws.columns:
            max_len = max((len(str(c.value or '')) for c in col_cells), default=10)
            ws.column_dimensions[col_cells[0].column_letter].width = min(max_len + 4, 40)

    buf.seek(0)
    resp = HttpResponse(buf.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    resp['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'
    return resp


def _to_pdf(df: pd.DataFrame, filename: str, title: str, columns: list) -> HttpResponse:
    try:
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        )
    except ImportError:
        return HttpResponse(
            'PDF export requires reportlab. Run: pip install reportlab',
            status=503
        )

    buf = io.BytesIO()
    page_size = landscape(A4) if len(columns) > 5 else A4
    doc = SimpleDocTemplate(buf, pagesize=page_size,
                            rightMargin=1.5*cm, leftMargin=1.5*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    story = []

    # Title
    story.append(Paragraph(title, styles['Heading1']))
    story.append(Paragraph(
        f'Generated: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}',
        styles['Normal']
    ))
    story.append(Spacer(1, 0.5*cm))

    # Table data
    data = [columns] + [[str(row[c]) for c in df.columns] for _, row in df.iterrows()]
    col_width = (doc.width) / len(columns)
    tbl = Table(data, colWidths=[col_width] * len(columns), repeatRows=1)
    tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2D6A4F')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F6F6F4')]),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#D0D0D0')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(tbl)
    doc.build(story)

    buf.seek(0)
    resp = HttpResponse(buf.read(), content_type='application/pdf')
    resp['Content-Disposition'] = f'attachment; filename="{filename}.pdf"'
    return resp
