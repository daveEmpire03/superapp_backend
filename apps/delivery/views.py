from django.db import transaction
from django.shortcuts import get_object_or_404

from rest_framework import generics
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.orders.models import Order
from apps.stores.permissions import (
    ensure_store_access,
    get_managed_store_ids,
    is_platform_admin,
)

from .models import (
    Delivery,
    DeliveryStatusHistory,
)
from .serializers import (
    AssignRiderSerializer,
    DeliverySerializer,
    RiderDeliveryStatusSerializer,
    StaffDeliveryCancelSerializer,
)
from .services import (
    assign_rider,
    cancel_delivery,
    update_rider_delivery_status,
)


STAFF_ROLES = {
    User.Role.ADMIN,
    User.Role.STORE_MANAGER,
    User.Role.STAFF,
}


def ensure_delivery_staff(user):
    if (
        not user.is_authenticated
        or user.role not in STAFF_ROLES
        and not user.is_superuser
    ):
        raise PermissionDenied("Staff access is required.")


def delivery_queryset():
    return Delivery.objects.select_related(
        "order",
        "order__user",
        "order__store",
        "rider",
    ).prefetch_related(
        "status_history",
        "status_history__changed_by",
    )


class CustomerDeliveryDetailView(generics.RetrieveAPIView):
    serializer_class = DeliverySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return delivery_queryset().filter(order__user=self.request.user)


class RiderDeliveriesView(generics.ListAPIView):
    serializer_class = DeliverySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role != User.Role.RIDER:
            raise PermissionDenied("Rider access is required.")

        queryset = delivery_queryset().filter(rider=self.request.user)

        status_value = self.request.query_params.get("status")

        if status_value:
            queryset = queryset.filter(status=status_value)

        return queryset


class RiderDeliveryStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        if request.user.role != User.Role.RIDER:
            raise PermissionDenied("Rider access is required.")

        serializer = RiderDeliveryStatusSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        delivery = get_object_or_404(
            Delivery,
            pk=pk,
            rider=request.user,
        )

        delivery = update_rider_delivery_status(
            delivery_id=delivery.id,
            rider=request.user,
            new_status=(serializer.validated_data["status"]),
            note=(
                serializer.validated_data.get(
                    "note",
                    "",
                )
            ),
            proof_note=(
                serializer.validated_data.get(
                    "proof_note",
                    "",
                )
            ),
        )

        delivery = delivery_queryset().get(id=delivery.id)

        return Response(DeliverySerializer(delivery).data)


class StaffDeliveryListView(generics.ListAPIView):
    serializer_class = DeliverySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        ensure_delivery_staff(self.request.user)

        queryset = delivery_queryset()

        if not is_platform_admin(self.request.user):
            store_ids = get_managed_store_ids(self.request.user)

            queryset = queryset.filter(order__store_id__in=store_ids)

        store_id = self.request.query_params.get("store")

        status_value = self.request.query_params.get("status")

        rider_id = self.request.query_params.get("rider")

        if store_id:
            queryset = queryset.filter(order__store_id=store_id)

        if status_value:
            queryset = queryset.filter(status=status_value)

        if rider_id:
            queryset = queryset.filter(rider_id=rider_id)

        return queryset


class StaffCreateDeliveryView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, order_id):
        ensure_delivery_staff(request.user)

        order = (
            Order.objects.select_for_update().select_related("store").get(id=order_id)
        )

        ensure_store_access(
            request.user,
            order.store_id,
        )

        if order.fulfilment_type != Order.Fulfilment.DELIVERY:
            from rest_framework.exceptions import ValidationError

            raise ValidationError(
                {"order": "Pickup orders do not " "require delivery."}
            )

        if order.payment_status != Order.PaymentStatus.PAID:
            from rest_framework.exceptions import ValidationError

            raise ValidationError(
                {"order": "The order must be paid " "before delivery is created."}
            )

        delivery, created = Delivery.objects.get_or_create(
            order=order,
            defaults={"status": Delivery.Status.PENDING},
        )

        if created:
            DeliveryStatusHistory.objects.create(
                delivery=delivery,
                status=Delivery.Status.PENDING,
                changed_by=request.user,
                note="Delivery created.",
            )

        delivery = delivery_queryset().get(id=delivery.id)

        return Response(
            DeliverySerializer(delivery).data,
            status=201 if created else 200,
        )


class StaffAssignRiderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        ensure_delivery_staff(request.user)

        delivery = get_object_or_404(
            Delivery.objects.select_related("order"),
            pk=pk,
        )

        ensure_store_access(
            request.user,
            delivery.order.store_id,
        )

        serializer = AssignRiderSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        rider = serializer.context["rider"]

        delivery = assign_rider(
            delivery_id=delivery.id,
            rider=rider,
            assigned_by=request.user,
        )

        delivery = delivery_queryset().get(id=delivery.id)

        return Response(DeliverySerializer(delivery).data)


class StaffCancelDeliveryView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        ensure_delivery_staff(request.user)

        delivery = get_object_or_404(
            Delivery.objects.select_related("order"),
            pk=pk,
        )

        ensure_store_access(
            request.user,
            delivery.order.store_id,
        )

        serializer = StaffDeliveryCancelSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        delivery = cancel_delivery(
            delivery_id=delivery.id,
            cancelled_by=request.user,
            reason=(
                serializer.validated_data.get(
                    "reason",
                    "",
                )
            ),
        )

        delivery = delivery_queryset().get(id=delivery.id)

        return Response(DeliverySerializer(delivery).data)
