from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from .models import Cart, CartItem


class CartItemInline(TabularInline):
    model = CartItem
    extra = 0
    autocomplete_fields = ("inventory",)


@admin.register(Cart)
class CartAdmin(ModelAdmin):
    list_display = ("user", "store", "updated_at")
    search_fields = ("user__username", "user__email", "store__name")
    autocomplete_fields = ("user", "store")
    readonly_fields = ("id", "created_at", "updated_at")
    inlines = (CartItemInline,)


@admin.register(CartItem)
class CartItemAdmin(ModelAdmin):
    list_display = ("cart", "inventory", "quantity", "updated_at")
    search_fields = ("cart__user__email", "inventory__product__name")
    autocomplete_fields = ("cart", "inventory")
    readonly_fields = ("id", "created_at", "updated_at")
