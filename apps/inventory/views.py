from django.db import transaction
from .models import (
    InventoryMovement,
    StoreInventory,
)
from rest_framework import (
    generics,
    permissions,
    status,
)
from rest_framework.exceptions import (
    PermissionDenied,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.stores.permissions import (
    ensure_store_access,
    get_managed_store_ids,
    is_platform_admin,
)

from .models import StoreInventory
from .serializers import (
    InventoryCreateSerializer,
    InventoryStockAdjustmentSerializer,
    InventoryUpdateSerializer,
    StoreInventorySerializer,
)


STAFF_ROLES = {
    User.Role.ADMIN,
    User.Role.STORE_MANAGER,
    User.Role.STAFF,
}


def ensure_inventory_staff(user):
    if not (user.is_superuser or user.role in STAFF_ROLES):
        raise PermissionDenied("You do not have permission " "to manage inventory.")


def inventory_queryset():
    return StoreInventory.objects.select_related(
        "store",
        "product",
    )


class InventoryListView(generics.ListAPIView):
    """
    Public customer-facing inventory.

    Only active stores, active products and
    available inventory are exposed.
    """

    serializer_class = StoreInventorySerializer
    permission_classes = [permissions.AllowAny]

    filterset_fields = [
        "store",
        "product",
        "is_available",
    ]

    search_fields = [
        "product__name",
        "product__brand",
        "product__sku",
    ]

    def get_queryset(self):
        return inventory_queryset().filter(
            store__is_active=True,
            product__is_active=True,
            is_available=True,
        )


class StaffInventoryListView(generics.ListAPIView):
    serializer_class = StoreInventorySerializer

    filterset_fields = [
        "store",
        "product",
        "is_available",
    ]

    search_fields = [
        "product__name",
        "product__brand",
        "product__sku",
    ]

    def get_queryset(self):
        ensure_inventory_staff(self.request.user)

        queryset = inventory_queryset().order_by(
            "store__name",
            "product__name",
        )

        if not is_platform_admin(self.request.user):
            store_ids = get_managed_store_ids(self.request.user)

            queryset = queryset.filter(store_id__in=store_ids)

        return queryset


class StaffInventoryCreateView(APIView):

    @transaction.atomic
    def post(self, request):
        ensure_inventory_staff(request.user)

        serializer = InventoryCreateSerializer(
            data=request.data,
        )

        serializer.is_valid(raise_exception=True)

        store = serializer.validated_data["store"]

        ensure_store_access(
            request.user,
            store.id,
        )

        inventory = serializer.save()

        inventory = inventory_queryset().get(id=inventory.id)

        return Response(
            {
                "success": True,
                "message": ("Inventory created " "successfully."),
                "data": StoreInventorySerializer(inventory).data,
            },
            status=status.HTTP_201_CREATED,
        )


class StaffInventoryDetailView(APIView):

    def get_inventory(
        self,
        request,
        pk,
        *,
        for_update=False,
    ):
        ensure_inventory_staff(request.user)

        queryset = inventory_queryset()

        if for_update:
            queryset = queryset.select_for_update()

        try:
            inventory = queryset.get(pk=pk)

        except StoreInventory.DoesNotExist:
            return None

        ensure_store_access(
            request.user,
            inventory.store_id,
        )

        return inventory

    def get(self, request, pk):
        inventory = self.get_inventory(
            request,
            pk,
        )

        if inventory is None:
            return Response(
                {
                    "success": False,
                    "error": {"inventory": ("Inventory not found.")},
                },
                status=(status.HTTP_404_NOT_FOUND),
            )

        return Response(
            {
                "success": True,
                "data": StoreInventorySerializer(inventory).data,
            }
        )

    @transaction.atomic
    def patch(self, request, pk):
        inventory = self.get_inventory(
            request,
            pk,
            for_update=True,
        )

        if inventory is None:
            return Response(
                {
                    "success": False,
                    "error": {"inventory": ("Inventory not found.")},
                },
                status=(status.HTTP_404_NOT_FOUND),
            )

        serializer = InventoryUpdateSerializer(
            data=request.data,
            context={
                "inventory": inventory,
            },
        )

        serializer.is_valid(raise_exception=True)

        for field, value in serializer.validated_data.items():
            setattr(
                inventory,
                field,
                value,
            )

        inventory.save()

        inventory = inventory_queryset().get(id=inventory.id)

        return Response(
            {
                "success": True,
                "message": ("Inventory updated " "successfully."),
                "data": StoreInventorySerializer(inventory).data,
            }
        )


class StaffInventoryStockAdjustmentView(APIView):

    @transaction.atomic
    def post(self, request, pk):
        ensure_inventory_staff(request.user)

        try:
            inventory = inventory_queryset().select_for_update().get(pk=pk)

        except StoreInventory.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "error": {"inventory": ("Inventory not found.")},
                },
                status=(status.HTTP_404_NOT_FOUND),
            )

        ensure_store_access(
            request.user,
            inventory.store_id,
        )

        serializer = InventoryStockAdjustmentSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        adjustment = serializer.validated_data["quantity"]

        new_quantity = inventory.quantity + adjustment

        # Physical stock may never become smaller
        # than units already reserved by checkouts.
        if new_quantity < inventory.reserved_quantity:
            return Response(
                {
                    "success": False,
                    "error": {
                        "quantity": (
                            "Stock cannot be reduced " "below reserved quantity."
                        )
                    },
                },
                status=(status.HTTP_409_CONFLICT),
            )

        if new_quantity < 0:
            return Response(
                {
                    "success": False,
                    "error": {"quantity": ("Stock cannot become " "negative.")},
                },
                status=(status.HTTP_409_CONFLICT),
            )

        inventory.quantity = new_quantity

        inventory.save(
            update_fields=[
                "quantity",
                "updated_at",
            ]
        )

        inventory = inventory_queryset().get(id=inventory.id)

        return Response(
            {
                "success": True,
                "message": ("Stock adjusted successfully."),
                "data": StoreInventorySerializer(inventory).data,
            }
        )
