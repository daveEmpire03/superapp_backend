import uuid

from django.db.models import Count, F, Prefetch, Q
from rest_framework import generics, permissions
from rest_framework.exceptions import ValidationError

from apps.inventory.models import StoreInventory

from .models import Category, Product
from .serializers import CategorySerializer, ProductSerializer


class CategoryListView(generics.ListAPIView):
    serializer_class = CategorySerializer
    permission_classes = [
        permissions.AllowAny,
    ]
    pagination_class = None

    def get_queryset(self):
        return (
            Category.objects.filter(is_active=True)
            .annotate(
                item_count=Count(
                    "products",
                    filter=Q(
                        products__is_active=True,
                    ),
                    distinct=True,
                ),
            )
            .order_by(
                "sort_order",
                "name",
            )
        )


class StoreScopedProductMixin:
    def get_store_id(self):
        raw_store_id = self.request.query_params.get(
            "store_id",
        )

        if not raw_store_id:
            return None

        try:
            return uuid.UUID(raw_store_id)
        except (TypeError, ValueError, AttributeError):
            raise ValidationError({"store_id": ("A valid store UUID is required.")})

    def get_base_queryset(self):
        return Product.objects.filter(
            is_active=True,
            category__is_active=True,
        ).select_related(
            "category",
        )

    def scope_to_store(
        self,
        queryset,
        store_id,
    ):
        if store_id is None:
            return queryset

        return queryset.filter(
            store_inventory__store_id=store_id,
            store_inventory__store__is_active=True,
            store_inventory__is_available=True,
        ).distinct()

    def attach_store_inventory(
        self,
        queryset,
        store_id,
    ):
        if store_id is None:
            return queryset

        inventory_queryset = StoreInventory.objects.filter(
            store_id=store_id,
            store__is_active=True,
        ).select_related(
            "store",
        )

        return queryset.prefetch_related(
            Prefetch(
                "store_inventory",
                queryset=inventory_queryset,
                to_attr=("_selected_store_inventory"),
            ),
        )

    def build_product_queryset(self):
        store_id = self.get_store_id()

        queryset = self.get_base_queryset()

        queryset = self.scope_to_store(
            queryset,
            store_id,
        )

        queryset = self.attach_store_inventory(
            queryset,
            store_id,
        )

        return queryset, store_id

    def apply_category_filter(
        self,
        queryset,
    ):
        category = self.request.query_params.get(
            "category",
        )

        if not category:
            return queryset

        try:
            category_id = uuid.UUID(category)

            return queryset.filter(
                category_id=category_id,
            )
        except (TypeError, ValueError, AttributeError):
            return queryset.filter(
                category__slug=category,
            )


class ProductListView(
    StoreScopedProductMixin,
    generics.ListAPIView,
):
    serializer_class = ProductSerializer
    permission_classes = [
        permissions.AllowAny,
    ]

    def get_queryset(self):
        queryset, _ = self.build_product_queryset()

        queryset = self.apply_category_filter(
            queryset,
        )

        search = self.request.query_params.get(
            "search",
            "",
        ).strip()

        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(brand__icontains=search)
                | Q(sku__icontains=search)
                | Q(category__name__icontains=search)
            )

        return queryset.order_by(
            "category__sort_order",
            "name",
        )


class ProductDealsView(
    StoreScopedProductMixin,
    generics.ListAPIView,
):
    serializer_class = ProductSerializer
    permission_classes = [
        permissions.AllowAny,
    ]

    def get_queryset(self):
        queryset, store_id = self.build_product_queryset()

        if store_id is None:
            return queryset.none()

        return (
            queryset.filter(
                store_inventory__store_id=store_id,
                store_inventory__is_available=True,
                store_inventory__compare_at_price__isnull=False,
                store_inventory__compare_at_price__gt=F(
                    "store_inventory__price",
                ),
            )
            .distinct()
            .order_by(
                "-updated_at",
            )
        )


class ProductSearchView(
    StoreScopedProductMixin,
    generics.ListAPIView,
):
    serializer_class = ProductSerializer
    permission_classes = [
        permissions.AllowAny,
    ]

    def get_queryset(self):
        query = self.request.query_params.get(
            "q",
            "",
        ).strip()

        if not query:
            return Product.objects.none()

        queryset, _ = self.build_product_queryset()

        return (
            queryset.filter(
                Q(name__icontains=query)
                | Q(brand__icontains=query)
                | Q(sku__icontains=query)
                | Q(category__name__icontains=query)
            )
            .distinct()
            .order_by(
                "name",
            )
        )


class ProductDetailView(
    StoreScopedProductMixin,
    generics.RetrieveAPIView,
):
    serializer_class = ProductSerializer
    permission_classes = [
        permissions.AllowAny,
    ]

    def get_queryset(self):
        queryset, _ = self.build_product_queryset()

        return queryset
