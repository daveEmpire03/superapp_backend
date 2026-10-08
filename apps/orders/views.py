from django.db import transaction

from rest_framework import (
    generics,
    status,
)
from rest_framework.exceptions import (
    PermissionDenied,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.loyalty.services import (
    award_order_points,
)
from apps.promotions.models import (
    PromotionRedemption,
)
from apps.stores.permissions import (
    ensure_store_access,
    get_managed_store_ids,
    is_platform_admin,
)

from .inventory_service import (
    InventoryReservationError,
    release_reserved_inventory,
)
from .models import (
    Order,
    OrderStatusHistory,
)
from .serializers import (
    CheckoutSerializer,
    OrderSerializer,
)
from .services import create_checkout


STAFF_ROLES = {
    User.Role.ADMIN,
    User.Role.STORE_MANAGER,
    User.Role.STAFF,
}


def get_order_queryset():
    return Order.objects.select_related(
        "store",
        "user",
    ).prefetch_related(
        "items",
        "status_history",
    )


def ensure_staff(user):
    if not (user.is_superuser or user.role in STAFF_ROLES):
        raise PermissionDenied("You do not have permission " "to manage orders.")


class OrderListView(generics.ListAPIView):
    serializer_class = OrderSerializer

    def get_queryset(self):
        return (
            get_order_queryset().filter(user=self.request.user).order_by("-created_at")
        )


class OrderDetailView(generics.RetrieveAPIView):
    serializer_class = OrderSerializer

    def get_queryset(self):
        return get_order_queryset().filter(user=self.request.user)


class CheckoutView(APIView):

    def post(self, request):
        serializer = CheckoutSerializer(
            data=request.data,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        order = create_checkout(
            user=request.user,
            fulfilment_type=(serializer.validated_data["fulfilment_type"]),
            delivery_address=(serializer.validated_data.get("delivery_address")),
            notes=(
                serializer.validated_data.get(
                    "notes",
                    "",
                )
            ),
            promotion_code=(
                serializer.validated_data.get(
                    "promotion_code",
                    "",
                )
            ),
        )

        order = get_order_queryset().get(id=order.id)

        return Response(
            {
                "success": True,
                "message": ("Checkout created " "successfully."),
                "data": (OrderSerializer(order).data),
            },
            status=status.HTTP_201_CREATED,
        )


class StaffOrderListView(generics.ListAPIView):
    serializer_class = OrderSerializer

    def get_queryset(self):
        ensure_staff(self.request.user)

        queryset = get_order_queryset().order_by("-created_at")

        if not is_platform_admin(self.request.user):
            store_ids = get_managed_store_ids(self.request.user)

            queryset = queryset.filter(store_id__in=store_ids)

        store_id = self.request.query_params.get("store")

        order_status = self.request.query_params.get("status")

        payment_status = self.request.query_params.get("payment_status")

        if store_id:
            queryset = queryset.filter(store_id=store_id)

        if order_status:
            queryset = queryset.filter(status=order_status)

        if payment_status:
            queryset = queryset.filter(payment_status=payment_status)

        return queryset


class StaffOrderStatusView(APIView):

    allowed_transitions = {
        Order.Status.PENDING: {
            Order.Status.CANCELLED,
        },
        Order.Status.CONFIRMED: {
            Order.Status.PREPARING,
        },
        Order.Status.PREPARING: {
            Order.Status.READY,
        },
        Order.Status.READY: {
            Order.Status.DISPATCHED,
        },
        Order.Status.DISPATCHED: {
            Order.Status.OUT_FOR_DELIVERY,
        },
        Order.Status.OUT_FOR_DELIVERY: {
            Order.Status.DELIVERED,
        },
    }

    @transaction.atomic
    def patch(
        self,
        request,
        pk,
    ):
        ensure_staff(request.user)

        try:
            order = (
                Order.objects.select_for_update()
                .select_related(
                    "store",
                    "user",
                )
                .get(pk=pk)
            )

        except Order.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "error": {"order": "Order not found."},
                },
                status=(status.HTTP_404_NOT_FOUND),
            )

        ensure_store_access(
            request.user,
            order.store_id,
        )

        new_status = request.data.get("status")

        note = request.data.get(
            "note",
            "",
        )

        if not new_status:
            return Response(
                {
                    "success": False,
                    "error": {"status": "Status is required."},
                },
                status=(status.HTTP_400_BAD_REQUEST),
            )

        valid_statuses = {value for value, _ in Order.Status.choices}

        if new_status not in valid_statuses:
            return Response(
                {
                    "success": False,
                    "error": {"status": "Invalid order status."},
                },
                status=(status.HTTP_400_BAD_REQUEST),
            )

        allowed = self.allowed_transitions.get(
            order.status,
            set(),
        )

        if new_status not in allowed:
            return Response(
                {
                    "success": False,
                    "error": {
                        "status": (
                            "Cannot move order from "
                            f"{order.status} to "
                            f"{new_status}."
                        )
                    },
                },
                status=(status.HTTP_400_BAD_REQUEST),
            )

        if new_status == Order.Status.CANCELLED:
            if (
                order.payment_status == Order.PaymentStatus.PAID
                or order.inventory_committed
            ):
                return Response(
                    {
                        "success": False,
                        "error": {
                            "order": (
                                "Paid orders cannot "
                                "be cancelled through "
                                "this endpoint. Use "
                                "the refund workflow."
                            )
                        },
                    },
                    status=(status.HTTP_409_CONFLICT),
                )

            try:
                release_reserved_inventory(
                    order,
                    performed_by=request.user,
                    reason=("Unpaid order cancelled " "by staff."),
                )

            except InventoryReservationError as exc:
                return Response(
                    {
                        "success": False,
                        "error": {"inventory": str(exc)},
                    },
                    status=(status.HTTP_409_CONFLICT),
                )

            PromotionRedemption.objects.filter(order=order).delete()

            order.status = Order.Status.CANCELLED

            order.reservation_expires_at = None

            order.save(
                update_fields=[
                    "status",
                    "reservation_expires_at",
                    "updated_at",
                ]
            )

        else:
            if order.payment_status != Order.PaymentStatus.PAID:
                return Response(
                    {
                        "success": False,
                        "error": {
                            "payment": ("Order must be paid " "before fulfilment.")
                        },
                    },
                    status=(status.HTTP_400_BAD_REQUEST),
                )

            order.status = new_status

            order.save(
                update_fields=[
                    "status",
                    "updated_at",
                ]
            )

            # Loyalty is earned only after a paid
            # order has actually been delivered.
            if new_status == Order.Status.DELIVERED:
                award_order_points(order)

        OrderStatusHistory.objects.create(
            order=order,
            status=new_status,
            note=note,
        )

        order = get_order_queryset().get(id=order.id)

        return Response(
            {
                "success": True,
                "message": "Order status updated.",
                "data": (OrderSerializer(order).data),
            }
        )
