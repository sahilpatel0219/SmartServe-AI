"""
SmartServe AI — REST API URL routing.

All endpoints are prefixed with /api/ (see smartserve/urls.py). Auth is JWT
(Authorization: Bearer <access>). Multi-tenant scoping: send the active
business via the X-Business-Id header (or ?business_id=), otherwise the user's
first active membership is used. Every endpoint re-validates the business
against a real Membership row — the client value is never trusted blindly.
"""
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import (
    views_auth, views_dashboard, views_onboarding, views_catalog, views_inventory,
    views_orders, views_customers, views_staff, views_suppliers, views_analytics,
    views_ml, views_assistant, views_notifications, views_reports,
)

app_name = 'api'

urlpatterns = [
    # ── Auth ──────────────────────────────────────────────────────────────────
    path('auth/register/', views_auth.RegisterView.as_view(), name='register'),
    path('auth/login/', views_auth.LoginView.as_view(), name='login'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/me/', views_auth.MeView.as_view(), name='me'),
    path('auth/login-history/', views_auth.LoginHistoryView.as_view(), name='login_history'),

    # ── Businesses / onboarding ───────────────────────────────────────────────
    path('businesses/', views_auth.BusinessListCreateView.as_view(), name='businesses'),
    path('businesses/<int:business_id>/', views_auth.BusinessDetailView.as_view(), name='business_detail'),
    path('businesses/<int:business_id>/activate/', views_auth.BusinessActivateView.as_view(), name='business_activate'),

    # ── Dashboard ─────────────────────────────────────────────────────────────
    path('dashboard/', views_dashboard.DashboardView.as_view(), name='dashboard'),

    # ── Data upload ───────────────────────────────────────────────────────────
    path('uploads/', views_onboarding.UploadCenterView.as_view(), name='upload_center'),
    path('uploads/<str:upload_type>/', views_onboarding.UploadFileView.as_view(), name='upload_file'),
    path('uploads/<str:upload_type>/template/', views_onboarding.DownloadTemplateView.as_view(), name='upload_template'),

    # ── Menu / catalog ────────────────────────────────────────────────────────
    path('menu/', views_catalog.MenuItemListCreateView.as_view(), name='menu'),
    path('menu/<str:item_id>/', views_catalog.MenuItemDetailView.as_view(), name='menu_detail'),

    # ── Inventory ─────────────────────────────────────────────────────────────
    path('inventory/', views_inventory.InventoryListCreateView.as_view(), name='inventory'),
    path('inventory/<str:item_id>/', views_inventory.InventoryDetailView.as_view(), name='inventory_detail'),

    # ── Orders ────────────────────────────────────────────────────────────────
    path('orders/', views_orders.OrderListCreateView.as_view(), name='orders'),
    path('orders/<str:order_id>/', views_orders.OrderDetailView.as_view(), name='order_detail'),
    path('orders/<str:order_id>/status/', views_orders.OrderStatusView.as_view(), name='order_status'),

    # ── Customers ─────────────────────────────────────────────────────────────
    path('customers/', views_customers.CustomerListCreateView.as_view(), name='customers'),
    path('customers/<str:customer_id>/', views_customers.CustomerDetailView.as_view(), name='customer_detail'),

    # ── Staff ─────────────────────────────────────────────────────────────────
    path('staff/', views_staff.EmployeeListCreateView.as_view(), name='staff'),
    path('staff/attendance/', views_staff.AttendanceView.as_view(), name='attendance'),
    path('staff/<str:employee_id>/', views_staff.EmployeeDetailView.as_view(), name='staff_detail'),

    # ── Suppliers ─────────────────────────────────────────────────────────────
    path('suppliers/', views_suppliers.SupplierListCreateView.as_view(), name='suppliers'),
    path('suppliers/purchase-orders/', views_suppliers.PurchaseOrderListCreateView.as_view(), name='purchase_orders'),
    path('suppliers/<str:supplier_id>/', views_suppliers.SupplierDetailView.as_view(), name='supplier_detail'),

    # ── Analytics ─────────────────────────────────────────────────────────────
    path('analytics/', views_analytics.AnalyticsView.as_view(), name='analytics'),

    # ── ML engine ─────────────────────────────────────────────────────────────
    path('ml/status/', views_ml.MLStatusView.as_view(), name='ml_status'),
    path('ml/run/', views_ml.RunAnalysisView.as_view(), name='ml_run'),
    path('ml/results/', views_ml.MLResultsView.as_view(), name='ml_results'),
    path('ml/insights/', views_ml.MLInsightsView.as_view(), name='ml_insights'),

    # ── Assistant ─────────────────────────────────────────────────────────────
    path('assistant/status/', views_assistant.AssistantStatusView.as_view(), name='assistant_status'),
    path('assistant/chat/', views_assistant.AssistantChatView.as_view(), name='assistant_chat'),
    path('assistant/feedback/', views_assistant.AssistantFeedbackView.as_view(), name='assistant_feedback'),

    # ── Notifications ─────────────────────────────────────────────────────────
    path('notifications/', views_notifications.NotificationListView.as_view(), name='notifications'),
    path('notifications/mark-all-read/', views_notifications.NotificationMarkAllReadView.as_view(), name='notifications_mark_all'),
    path('notifications/<str:notif_id>/read/', views_notifications.NotificationMarkReadView.as_view(), name='notification_read'),

    # ── Reports (binary downloads — plain Django views w/ manual JWT) ──────────
    path('reports/status/', views_reports.reports_status_view, name='reports_status'),
    path('reports/export/<str:report_type>/<str:fmt>/', views_reports.export_view, name='reports_export'),
]
