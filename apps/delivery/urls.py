from django.urls import path

from .views import (
    CustomerDeliveryDetailView,
    RiderDeliveriesView,
    RiderDeliveryStatusView,
    StaffAssignRiderView,
    StaffCancelDeliveryView,
    StaffCreateDeliveryView,
    StaffDeliveryListView,
)


urlpatterns = [
    # Customer
    path(
        "<uuid:pk>/",
        CustomerDeliveryDetailView.as_view(),
        name="customer-delivery-detail",
    ),
    # Rider
    path(
        "rider/mine/",
        RiderDeliveriesView.as_view(),
        name="rider-deliveries",
    ),
    path(
        "rider/<uuid:pk>/status/",
        RiderDeliveryStatusView.as_view(),
        name="rider-delivery-status",
    ),
    # Store staff / admin
    path(
        "staff/",
        StaffDeliveryListView.as_view(),
        name="staff-deliveries",
    ),
    path(
        "staff/orders/<uuid:order_id>/create/",
        StaffCreateDeliveryView.as_view(),
        name="staff-create-delivery",
    ),
    path(
        "staff/<uuid:pk>/assign/",
        StaffAssignRiderView.as_view(),
        name="staff-assign-rider",
    ),
    path(
        "staff/<uuid:pk>/cancel/",
        StaffCancelDeliveryView.as_view(),
        name="staff-cancel-delivery",
    ),
]
