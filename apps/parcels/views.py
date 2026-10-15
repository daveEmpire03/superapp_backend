import secrets
from datetime import timedelta
from decimal import Decimal
from math import cos, radians
import os

from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.rides.models import Ride, RideDriverProfile
from apps.rides.pricing import haversine_distance_km
DRIVER_LOCATION_MAX_AGE = timedelta(seconds=int(os.getenv("DRIVER_LOCATION_MAX_AGE_SECONDS", "300")))
DRIVER_SEARCH_RADIUS_KM = float(os.getenv("DRIVER_SEARCH_RADIUS_KM", "10"))

from .models import ParcelShipment, ParcelStatusHistory
from .pricing import quote_parcel
from .serializers import (
    ParcelCancelSerializer,
    ParcelCreateSerializer,
    ParcelDriverStatusSerializer,
    ParcelQuoteRequestSerializer,
    ParcelShipmentSerializer,
)


ACTIVE_RIDE_STATUSES = (
    Ride.Status.DRIVER_ASSIGNED,
    Ride.Status.DRIVER_ARRIVING,
    Ride.Status.IN_PROGRESS,
)
ACTIVE_PARCEL_STATUSES = (
    ParcelShipment.Status.DRIVER_ASSIGNED,
    ParcelShipment.Status.PICKED_UP,
    ParcelShipment.Status.IN_TRANSIT,
)


def notify_after_commit(*, user, title, message, notification_type, data):
    from apps.notifications.services import create_notification

    transaction.on_commit(lambda: create_notification(
        user=user, title=title, message=message,
        notification_type=notification_type, data=data,
    ))


def notify_nearby_drivers_for_parcel(parcel):
    if parcel.payment_method == ParcelShipment.PaymentMethod.ONLINE and parcel.payment_status != ParcelShipment.PaymentStatus.PAID:
        return
    from apps.notifications.models import Notification

    latitude = float(parcel.pickup_latitude)
    longitude = float(parcel.pickup_longitude)
    latitude_delta = DRIVER_SEARCH_RADIUS_KM / 110.574
    longitude_delta = DRIVER_SEARCH_RADIUS_KM / max(111.320 * abs(cos(radians(latitude))), 11.132)
    vehicle_types = ["CAR"] if parcel.package_size == ParcelShipment.PackageSize.LARGE else ["CAR", "MOTORCYCLE"]
    profiles = RideDriverProfile.objects.select_related("user").filter(
        vehicle_type__in=vehicle_types,
        is_approved=True,
        is_suspended=False,
        is_available=True,
        last_location_at__gte=timezone.now() - DRIVER_LOCATION_MAX_AGE,
        current_latitude__gte=Decimal(str(latitude - latitude_delta)),
        current_latitude__lte=Decimal(str(latitude + latitude_delta)),
        current_longitude__gte=Decimal(str(longitude - longitude_delta)),
        current_longitude__lte=Decimal(str(longitude + longitude_delta)),
    )
    for profile in profiles:
        distance = haversine_distance_km(
            profile.current_latitude, profile.current_longitude,
            parcel.pickup_latitude, parcel.pickup_longitude,
        )
        if distance <= DRIVER_SEARCH_RADIUS_KM:
            notify_after_commit(
                user=profile.user,
                title="New nearby parcel request",
                message=f"A {parcel.package_size.lower()} parcel is available for pickup nearby.",
                notification_type=Notification.Type.DELIVERY,
                data={"service": "PARCEL", "parcel_id": str(parcel.pk), "status": parcel.status},
            )


def ensure_customer(user):
    if user.role != User.Role.CUSTOMER:
        raise PermissionDenied("Only customer accounts can create parcel shipments.")


def ensure_driver(user):
    if user.role != User.Role.RIDER or not user.is_active:
        raise PermissionDenied("An active driver account is required.")


def parcel_queryset():
    return (
        ParcelShipment.objects.select_related("sender", "driver", "driver__ride_driver_profile")
        .prefetch_related("status_history", "status_history__changed_by")
    )


def require_approved_driver(profile):
    if not profile.is_approved or profile.is_suspended:
        raise PermissionDenied("Your driver profile is not approved for dispatch.")
    if (
        profile.current_latitude is None
        or profile.current_longitude is None
        or profile.last_location_at is None
        or profile.last_location_at < timezone.now() - DRIVER_LOCATION_MAX_AGE
    ):
        raise ValidationError({"location": "Update your location before accepting parcels."})


def driver_has_active_work(driver):
    return (
        Ride.objects.filter(driver=driver, status__in=ACTIVE_RIDE_STATUSES).exists()
        or ParcelShipment.objects.filter(driver=driver, status__in=ACTIVE_PARCEL_STATUSES).exists()
    )


def record_history(parcel, new_status, actor, note=""):
    ParcelStatusHistory.objects.create(
        parcel=parcel,
        status=new_status,
        changed_by=actor,
        note=note,
    )


class ParcelQuoteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ensure_customer(request.user)
        serializer = ParcelQuoteRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        quote = quote_parcel(serializer.validated_data)
        return Response({
            "success": True,
            "message": "Estimated parcel delivery fare calculated.",
            "data": quote,
        })


class ParcelListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ParcelShipmentSerializer

    def get_queryset(self):
        ensure_customer(self.request.user)
        queryset = parcel_queryset().filter(sender=self.request.user)
        status_value = self.request.query_params.get("status")
        if status_value:
            valid_statuses = {value for value, _ in ParcelShipment.Status.choices}
            if status_value not in valid_statuses:
                return queryset.none()
            queryset = queryset.filter(status=status_value)
        return queryset

    def create(self, request, *args, **kwargs):
        ensure_customer(request.user)
        serializer = ParcelCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        quote = quote_parcel(data)
        delivery_code = f"{secrets.randbelow(1_000_000):06d}"

        with transaction.atomic():
            parcel = ParcelShipment.objects.create(
                sender=request.user,
                package_size=data["package_size"],
                package_description=data["package_description"],
                recipient_name=data["recipient_name"],
                recipient_phone=data["recipient_phone"],
                pickup_address=data["pickup_address"],
                pickup_latitude=data["pickup_latitude"],
                pickup_longitude=data["pickup_longitude"],
                destination_address=data["destination_address"],
                destination_latitude=data["destination_latitude"],
                destination_longitude=data["destination_longitude"],
                estimated_distance_km=quote["estimated_distance_km"],
                quoted_fare=quote["quoted_fare"],
                currency=quote["currency"],
                payment_method=data["payment_method"],
                payment_status=ParcelShipment.PaymentStatus.UNPAID,
                status=ParcelShipment.Status.REQUESTED,
                delivery_code_hash=make_password(delivery_code),
            )
            record_history(parcel, ParcelShipment.Status.REQUESTED, request.user, "Parcel shipment requested.")
            notify_nearby_drivers_for_parcel(parcel)

        parcel = parcel_queryset().get(pk=parcel.pk)
        return Response({
            "success": True,
            "message": "Parcel shipment requested. Share the delivery code with the recipient.",
            "data": {
                **ParcelShipmentSerializer(parcel, context=self.get_serializer_context()).data,
                "delivery_code": delivery_code,
            },
        }, status=status.HTTP_201_CREATED)


class ParcelDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ParcelShipmentSerializer

    def get_queryset(self):
        ensure_customer(self.request.user)
        return parcel_queryset().filter(sender=self.request.user)


class ParcelCancelView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        ensure_customer(request.user)
        serializer = ParcelCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            parcel = get_object_or_404(
                ParcelShipment.objects.select_for_update(), pk=pk, sender=request.user
            )
            if parcel.status in {ParcelShipment.Status.PICKED_UP, ParcelShipment.Status.IN_TRANSIT, ParcelShipment.Status.DELIVERED}:
                raise ValidationError({"parcel": "A parcel cannot be cancelled after pickup."})
            if parcel.status == ParcelShipment.Status.CANCELLED:
                return Response({"success": True, "data": ParcelShipmentSerializer(parcel).data})
            if parcel.payment_status in {ParcelShipment.PaymentStatus.PAID, ParcelShipment.PaymentStatus.PENDING}:
                raise ValidationError({"payment": "A parcel with an online payment requires reconciliation/refund handling before cancellation."})
            parcel.status = ParcelShipment.Status.CANCELLED
            parcel.cancelled_at = timezone.now()
            parcel.save(update_fields=["status", "cancelled_at", "updated_at"])
            record_history(parcel, ParcelShipment.Status.CANCELLED, request.user, serializer.validated_data.get("reason", "") or "Cancelled by sender.")
            if parcel.driver_id:
                from apps.notifications.models import Notification
                notify_after_commit(
                    user=parcel.driver, title="Parcel cancelled",
                    message="The sender cancelled the parcel before pickup.",
                    notification_type=Notification.Type.DELIVERY,
                    data={"service": "PARCEL", "parcel_id": str(parcel.pk), "status": parcel.status},
                )
        parcel = parcel_queryset().get(pk=parcel.pk)
        return Response({"success": True, "data": ParcelShipmentSerializer(parcel).data})


class ParcelDriverMineView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ParcelShipmentSerializer

    def get_queryset(self):
        ensure_driver(self.request.user)
        return parcel_queryset().filter(
            driver=self.request.user,
            status__in=ACTIVE_PARCEL_STATUSES,
        )


class ParcelDriverAvailableView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        ensure_driver(request.user)
        profile = get_object_or_404(RideDriverProfile, user=request.user)
        require_approved_driver(profile)
        if not profile.is_available:
            raise ValidationError({"is_available": "Go available to view parcel requests."})
        if driver_has_active_work(request.user):
            raise ValidationError({"work": "Complete your active assignment before viewing more requests."})

        latitude = float(profile.current_latitude)
        longitude = float(profile.current_longitude)
        lat_delta = DRIVER_SEARCH_RADIUS_KM / 110.574
        lon_delta = DRIVER_SEARCH_RADIUS_KM / max(111.320 * abs(cos(radians(latitude))), 11.132)
        candidates = parcel_queryset().filter(
            status=ParcelShipment.Status.REQUESTED,
            pickup_latitude__gte=Decimal(str(latitude - lat_delta)),
            pickup_latitude__lte=Decimal(str(latitude + lat_delta)),
            pickup_longitude__gte=Decimal(str(longitude - lon_delta)),
            pickup_longitude__lte=Decimal(str(longitude + lon_delta)),
        )
        matches = []
        for parcel in candidates:
            if parcel.payment_method == ParcelShipment.PaymentMethod.ONLINE and parcel.payment_status != ParcelShipment.PaymentStatus.PAID:
                continue
            if profile.vehicle_type == "MOTORCYCLE" and parcel.package_size == ParcelShipment.PackageSize.LARGE:
                continue
            distance = haversine_distance_km(
                profile.current_latitude, profile.current_longitude,
                parcel.pickup_latitude, parcel.pickup_longitude,
            )
            if distance <= DRIVER_SEARCH_RADIUS_KM:
                matches.append((distance, parcel))
        matches.sort(key=lambda item: item[0])
        data = [
            {"pickup_distance_km": round(distance, 2), "parcel": ParcelShipmentSerializer(parcel).data}
            for distance, parcel in matches[:50]
        ]
        return Response({"success": True, "count": len(data), "data": data})


class ParcelDriverAcceptView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        ensure_driver(request.user)
        with transaction.atomic():
            profile = get_object_or_404(
                RideDriverProfile.objects.select_for_update(), user=request.user
            )
            parcel = get_object_or_404(ParcelShipment.objects.select_for_update(), pk=pk)
            require_approved_driver(profile)
            if not profile.is_available:
                raise ValidationError({"is_available": "You must be available to accept a parcel."})
            if driver_has_active_work(request.user):
                raise ValidationError({"work": "You already have an active assignment."})
            if parcel.status != ParcelShipment.Status.REQUESTED or parcel.driver_id:
                raise ValidationError({"parcel": "This parcel is no longer available."})
            if parcel.payment_method == ParcelShipment.PaymentMethod.ONLINE and parcel.payment_status != ParcelShipment.PaymentStatus.PAID:
                raise ValidationError({"payment": "Online payment must be verified before a courier can accept this parcel."})
            if profile.vehicle_type == "MOTORCYCLE" and parcel.package_size == ParcelShipment.PackageSize.LARGE:
                raise ValidationError({"package_size": "This parcel requires a car."})
            distance = haversine_distance_km(
                profile.current_latitude, profile.current_longitude,
                parcel.pickup_latitude, parcel.pickup_longitude,
            )
            if distance > DRIVER_SEARCH_RADIUS_KM:
                raise ValidationError({"parcel": "This pickup is outside your dispatch radius."})
            parcel.driver = request.user
            parcel.status = ParcelShipment.Status.DRIVER_ASSIGNED
            parcel.assigned_at = timezone.now()
            parcel.save(update_fields=["driver", "status", "assigned_at", "updated_at"])
            profile.is_available = False
            profile.save(update_fields=["is_available", "updated_at"])
            record_history(parcel, ParcelShipment.Status.DRIVER_ASSIGNED, request.user, "Driver accepted parcel.")
            from apps.notifications.models import Notification
            notify_after_commit(
                user=parcel.sender, title="Courier assigned",
                message="A courier has accepted your parcel shipment.",
                notification_type=Notification.Type.DELIVERY,
                data={"service": "PARCEL", "parcel_id": str(parcel.pk), "status": parcel.status},
            )
        parcel = parcel_queryset().get(pk=parcel.pk)
        return Response({"success": True, "data": ParcelShipmentSerializer(parcel).data})


class ParcelDriverStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        ensure_driver(request.user)
        serializer = ParcelDriverStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        with transaction.atomic():
            parcel = get_object_or_404(
                ParcelShipment.objects.select_for_update(), pk=pk, driver=request.user
            )
            if parcel.status == ParcelShipment.Status.DRIVER_ASSIGNED and data["status"] == ParcelShipment.Status.PICKED_UP:
                parcel.status = data["status"]
                parcel.picked_up_at = timezone.now()
                update_fields = ["status", "picked_up_at", "updated_at"]
            elif parcel.status == ParcelShipment.Status.PICKED_UP and data["status"] == ParcelShipment.Status.IN_TRANSIT:
                parcel.status = data["status"]
                parcel.in_transit_at = timezone.now()
                update_fields = ["status", "in_transit_at", "updated_at"]
            elif parcel.status == ParcelShipment.Status.IN_TRANSIT and data["status"] == ParcelShipment.Status.DELIVERED:
                if not check_password(data["delivery_code"], parcel.delivery_code_hash):
                    raise ValidationError({"delivery_code": "The delivery confirmation code is invalid."})
                parcel.status = data["status"]
                parcel.delivered_at = timezone.now()
                parcel.proof_note = data.get("proof_note", "")
                parcel.delivery_code_hash = make_password(secrets.token_urlsafe(32))
                update_fields = ["status", "delivered_at", "proof_note", "delivery_code_hash", "updated_at"]
            else:
                raise ValidationError({"status": f"Invalid parcel transition from {parcel.status} to {data['status']}."})
            parcel.save(update_fields=update_fields)
            record_history(parcel, parcel.status, request.user, data.get("proof_note", "") or f"Parcel status updated to {parcel.status}.")
            from apps.notifications.models import Notification
            notify_after_commit(
                user=parcel.sender, title="Parcel status updated",
                message=f"Your parcel is now {parcel.status.replace(chr(95), chr(32)).lower()}.",
                notification_type=Notification.Type.DELIVERY,
                data={"service": "PARCEL", "parcel_id": str(parcel.pk), "status": parcel.status},
            )
        parcel = parcel_queryset().get(pk=parcel.pk)
        return Response({"success": True, "data": ParcelShipmentSerializer(parcel).data})
