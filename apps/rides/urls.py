from django.urls import path

from .views import RideDetailView, RideListCreateView, RideQuoteView


urlpatterns = [
    path("quote/", RideQuoteView.as_view(), name="ride-quote"),
    path("", RideListCreateView.as_view(), name="ride-list-create"),
    path("<uuid:pk>/", RideDetailView.as_view(), name="ride-detail"),
]
