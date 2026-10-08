from django.contrib import admin

from .models import Category, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
        "sort_order",
        "is_active",
    )

    list_filter = ("is_active",)

    search_fields = (
        "name",
        "slug",
    )

    prepopulated_fields = {
        "slug": ("name",),
    }

    ordering = (
        "sort_order",
        "name",
    )

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "sku",
        "brand",
        "category",
        "size",
        "is_active",
        "created_at",
    )

    list_filter = (
        "is_active",
        "category",
        "brand",
    )

    search_fields = (
        "name",
        "sku",
        "brand",
        "description",
    )

    prepopulated_fields = {
        "slug": ("name",),
    }

    autocomplete_fields = ("category",)

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )
