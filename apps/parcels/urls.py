from django.urls import path

from .views import (
    ParcelCancelView,
    ParcelDetailView,
    ParcelListCreateView,
    ParcelQuoteView,
    ParcelDriverAcceptView,
    ParcelDriverAvailableView,
    ParcelDriverStatusView,
)


urlpatterns = [
    path("quote/", ParcelQuoteView.as_view(), name="parcel-quote"),
    path("driver/available/", ParcelDriverAvailableView.as_view(), name="parcel-driver-available"),
    path("<uuid:pk>/accept/", ParcelDriverAcceptView.as_view(), name="parcel-driver-accept"),
    path("<uuid:pk>/status/", ParcelDriverStatusView.as_view(), name="parcel-driver-status"),
    path("<uuid:pk>/cancel/", ParcelCancelView.as_view(), name="parcel-cancel"),
    path("", ParcelListCreateView.as_view(), name="parcel-list-create"),
    path("<uuid:pk>/", ParcelDetailView.as_view(), name="parcel-detail"),
]
