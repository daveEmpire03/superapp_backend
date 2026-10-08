from django.urls import path

from .views import (
    MyReviewDetailView,
    MyReviewListCreateView,
    ProductRatingSummaryView,
    ProductReviewListView,
    ReviewEligibilityView,
)


urlpatterns = [
    path(
        "",
        MyReviewListCreateView.as_view(),
        name="my-review-list-create",
    ),
    path(
        "<uuid:pk>/",
        MyReviewDetailView.as_view(),
        name="my-review-detail",
    ),
    path(
        "products/<uuid:product_id>/",
        ProductReviewListView.as_view(),
        name="product-review-list",
    ),
    path(
        "products/<uuid:product_id>/summary/",
        ProductRatingSummaryView.as_view(),
        name="product-rating-summary",
    ),
    path(
        "products/<uuid:product_id>/eligibility/",
        ReviewEligibilityView.as_view(),
        name="review-eligibility",
    ),
]
