from django.urls import path

from .views import (
    AcceptRideView,
    AvailableRideListView,
    DriverAvailabilityView,
    DriverLocationView,
    DriverProfileView,
    DriverRideStatusView,
    RideCancelView,
    RideDetailView,
    RideListCreateView,
    RideQuoteView,
)


urlpatterns = [
    path("quote/", RideQuoteView.as_view(), name="ride-quote"),
    path("driver/profile/", DriverProfileView.as_view(), name="ride-driver-profile"),
    path("driver/location/", DriverLocationView.as_view(), name="ride-driver-location"),
    path("driver/availability/", DriverAvailabilityView.as_view(), name="ride-driver-availability"),
    path("driver/available/", AvailableRideListView.as_view(), name="ride-driver-available-rides"),
    path("<uuid:pk>/accept/", AcceptRideView.as_view(), name="ride-accept"),
    path("<uuid:pk>/cancel/", RideCancelView.as_view(), name="ride-cancel"),
    path("<uuid:pk>/status/", DriverRideStatusView.as_view(), name="ride-driver-status"),
    path("", RideListCreateView.as_view(), name="ride-list-create"),
    path("<uuid:pk>/", RideDetailView.as_view(), name="ride-detail"),
]
