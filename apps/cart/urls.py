from django.urls import path

from .views import (
    AddCartItemView,
    ClearCartView,
    MyCartView,
    RemoveCartItemView,
    UpdateCartItemView,
)


urlpatterns = [
    path(
        "",
        MyCartView.as_view(),
        name="cart",
    ),
    path(
        "items/",
        AddCartItemView.as_view(),
        name="cart-add-item",
    ),
    path(
        "items/<uuid:item_id>/",
        UpdateCartItemView.as_view(),
        name="cart-update-item",
    ),
    path(
        "items/<uuid:item_id>/remove/",
        RemoveCartItemView.as_view(),
        name="cart-remove-item",
    ),
    path(
        "clear/",
        ClearCartView.as_view(),
        name="cart-clear",
    ),
]
