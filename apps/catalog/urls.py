from django.urls import path

from .views import (
    CategoryListView,
    ProductDealsView,
    ProductDetailView,
    ProductListView,
    ProductSearchView,
)


app_name = "catalog"


urlpatterns = [
    path(
        "categories/",
        CategoryListView.as_view(),
        name="category-list",
    ),
    path(
        "products/",
        ProductListView.as_view(),
        name="product-list",
    ),
    path(
        "products/deals/",
        ProductDealsView.as_view(),
        name="product-deals",
    ),
    path(
        "products/search/",
        ProductSearchView.as_view(),
        name="product-search",
    ),
    path(
        "products/<uuid:pk>/",
        ProductDetailView.as_view(),
        name="product-detail",
    ),
]
