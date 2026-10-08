from django.urls import path
from .views import (
    OrderListView,
    OrderDetailView,
    CheckoutView,
    StaffOrderListView,
    StaffOrderStatusView,
)

urlpatterns = [
    path("", OrderListView.as_view()),
    path("checkout/", CheckoutView.as_view()),
    path("<uuid:pk>/", OrderDetailView.as_view()),
    path("staff/all/", StaffOrderListView.as_view()),
    path("staff/<uuid:pk>/status/", StaffOrderStatusView.as_view()),
]
