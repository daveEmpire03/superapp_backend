from django.urls import path

from .views import (
    PromotionListView,
    PromotionValidateView,
    StaffPromotionDetailView,
    StaffPromotionListCreateView,
)


urlpatterns = [
    path(
        "",
        PromotionListView.as_view(),
        name="promotion-list",
    ),
    path(
        "validate/",
        PromotionValidateView.as_view(),
        name="promotion-validate",
    ),
    # Staff
    path(
        "staff/",
        StaffPromotionListCreateView.as_view(),
        name="staff-promotion-list-create",
    ),
    path(
        "staff/<uuid:pk>/",
        StaffPromotionDetailView.as_view(),
        name="staff-promotion-detail",
    ),
]
