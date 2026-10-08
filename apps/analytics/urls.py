from django.urls import path

from .views import (
    DashboardView,
    DeliveryPerformanceView,
    EventView,
    LowStockAnalyticsView,
    RevenueAnalyticsView,
    StorePerformanceView,
    TopProductsView,
)


urlpatterns = [
    path(
        "events/",
        EventView.as_view(),
        name="analytics-event",
    ),
    path(
        "dashboard/",
        DashboardView.as_view(),
        name="analytics-dashboard",
    ),
    path(
        "revenue/",
        RevenueAnalyticsView.as_view(),
        name="analytics-revenue",
    ),
    path(
        "products/top/",
        TopProductsView.as_view(),
        name="analytics-top-products",
    ),
    path(
        "stores/",
        StorePerformanceView.as_view(),
        name="analytics-store-performance",
    ),
    path(
        "inventory/low-stock/",
        LowStockAnalyticsView.as_view(),
        name="analytics-low-stock",
    ),
    path(
        "delivery/",
        DeliveryPerformanceView.as_view(),
        name="analytics-delivery-performance",
    ),
]
