from datetime import timedelta
from decimal import Decimal
from math import cos, radians
import os

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User

from .models import Ride, RideDriverProfile, RideStatusHistory
from .pricing import haversine_distance_km, quote_for_location_data
from .serializers import (
    DriverAvailabilitySerializer,
    DriverLocationSerializer,
    DriverRideStatusSerializer,
    RideCancelSerializer,
    RideCreateSerializer,
    RideDriverProfileSerializer,
    RideQuoteRequestSerializer,
    RideSerializer,
)


DRIVER_LOCATION_MAX_AGE = timedelta(seconds=int(os.getenv("DRIVER_LOCATION_MAX_AGE_SECONDS", "300")))
DRIVER_SEARCH_RADIUS_KM = float(os.getenv("DRIVER_SEARCH_RADIUS_KM", "10"))
ACTIVE_DRIVER_RIDE_STATUSES = (
    Ride.Status.DRIVER_ASSIGNED,
    Ride.Status.DRIVER_ARRIVING,
    Ride.Status.IN_PROGRESS,
)
ACCEPTABLE_RIDE_STATUSES = (Ride.Status.REQUESTED, Ride.Status.SEARCHING)
DRIVER_TRANSITIONS = {
    Ride.Status.DRIVER_ASSIGNED: Ride.Status.DRIVER_ARRIVING,
    Ride.Status.DRIVER_ARRIVING: Ride.Status.IN_PROGRESS,
    Ride.Status.IN_PROGRESS: Ride.Status.COMPLETED,
}


def notify_after_commit(*, user, title, message, notification_type, data):
    from apps.notifications.services import create_notification

    transaction.on_commit(lambda: create_notification(
        user=user, title=title, message=message,
        notification_type=notification_type, data=data,
    ))


def notify_nearby_drivers_for_ride(ride):
    from .pricing import haversine_distance_km
    from apps.notifications.models import Notification

    latitude = float(ride.pickup_latitude)
    longitude = float(ride.pickup_longitude)
    latitude_delta = DRIVER_SEARCH_RADIUS_KM / 110.574
    longitude_delta = DRIVER_SEARCH_RADIUS_KM / max(111.320 * abs(cos(radians(latitude))), 11.132)
    profiles = RideDriverProfile.objects.select_related("user").filter(
        vehicle_type=ride.vehicle_type,
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
            ride.pickup_latitude, ride.pickup_longitude,
        )
        if distance <= DRIVER_SEARCH_RADIUS_KM:
            notify_after_commit(
                user=profile.user,
                title="New nearby ride request",
                message=f"A {ride.vehicle_type.lower()} ride is available near your location.",
                notification_type=Notification.Type.DELIVERY,
                data={"service": "RIDE", "ride_id": str(ride.pk), "status": ride.status},
            )


def ensure_passenger(user):
    if user.role != User.Role.CUSTOMER:
        raise PermissionDenied("Only customer accounts can request passenger rides.")


def ensure_driver(user):
    if user.role != User.Role.RIDER:
        raise PermissionDenied("Only driver accounts can access driver ride operations.")
    if not user.is_active:
        raise PermissionDenied("Inactive driver accounts cannot perform ride operations.")


def ride_queryset():
    return (
        Ride.objects.select_related("passenger", "driver")
        .prefetch_related("status_history", "status_history__changed_by")
    )


def require_fresh_driver_location(profile):
    if (
        profile.current_latitude is None
        or profile.current_longitude is None
        or profile.last_location_at is None
        or profile.last_location_at < timezone.now() - DRIVER_LOCATION_MAX_AGE
    ):
        raise ValidationError(
            {"location": "Update your location before going available or accepting rides."}
        )


def has_active_ride(driver):
    return Ride.objects.filter(
        driver=driver,
        status__in=ACTIVE_DRIVER_RIDE_STATUSES,
    ).exists()


class RideQuoteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ensure_passenger(request.user)
        serializer = RideQuoteRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        quote = quote_for_location_data(serializer.validated_data)
        return Response(
            {
                "success": True,
                "message": "Estimated ride fare calculated.",
                "data": {
                    **quote,
                    "vehicle_type": serializer.validated_data["vehicle_type"],
                },
            },
            status=status.HTTP_200_OK,
        )


class RideListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = RideSerializer

    def get_queryset(self):
        ensure_passenger(self.request.user)
        queryset = ride_queryset().filter(passenger=self.request.user)

        status_value = self.request.query_params.get("status")
        if status_value:
            valid_statuses = {value for value, _ in Ride.Status.choices}
            if status_value not in valid_statuses:
                return queryset.none()
            queryset = queryset.filter(status=status_value)

        return queryset

    def create(self, request, *args, **kwargs):
        ensure_passenger(request.user)
        serializer = RideCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        quote = quote_for_location_data(data)

        with transaction.atomic():
            ride = Ride.objects.create(
                passenger=request.user,
                vehicle_type=data["vehicle_type"],
                status=Ride.Status.REQUESTED,
                pickup_address=data["pickup_address"],
                pickup_latitude=data["pickup_latitude"],
                pickup_longitude=data["pickup_longitude"],
                destination_address=data["destination_address"],
                destination_latitude=data["destination_latitude"],
                destination_longitude=data["destination_longitude"],
                quoted_fare=quote["quoted_fare"],
                currency=quote["currency"],
                payment_method=data["payment_method"],
                payment_status=Ride.PaymentStatus.UNPAID,
                passenger_note=data.get("passenger_note", ""),
            )
            RideStatusHistory.objects.create(
                ride=ride,
                status=Ride.Status.REQUESTED,
                changed_by=request.user,
                note="Ride requested by passenger.",
            )
            notify_nearby_drivers_for_ride(ride)

        ride = ride_queryset().get(pk=ride.pk)
        return Response(
            {
                "success": True,
                "message": "Ride requested successfully.",
                "data": RideSerializer(ride, context=self.get_serializer_context()).data,
            },
            status=status.HTTP_201_CREATED,
        )


class RideDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = RideSerializer
    lookup_field = "pk"

    def get_queryset(self):
        ensure_passenger(self.request.user)
        return ride_queryset().filter(passenger=self.request.user)


class RideCancelView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        ensure_passenger(request.user)
        serializer = RideCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            ride = get_object_or_404(
                Ride.objects.select_for_update(),
                pk=pk,
                passenger=request.user,
            )
            if ride.status not in {
                Ride.Status.REQUESTED,
                Ride.Status.SEARCHING,
                Ride.Status.DRIVER_ASSIGNED,
                Ride.Status.DRIVER_ARRIVING,
            }:
                raise ValidationError({"ride": "This ride can no longer be cancelled."})
            if ride.payment_status == Ride.PaymentStatus.PAID:
                raise ValidationError({
                    "payment": "This ride has a successful online payment and requires the refund workflow before cancellation."
                })

            ride.status = Ride.Status.CANCELLED
            ride.cancelled_at = timezone.now()
            ride.save(update_fields=["status", "cancelled_at", "updated_at"])
            RideStatusHistory.objects.create(
                ride=ride,
                status=Ride.Status.CANCELLED,
                changed_by=request.user,
                note=serializer.validated_data.get("reason", "") or "Cancelled by passenger.",
            )
            if ride.driver_id:
                from apps.notifications.models import Notification
                notify_after_commit(
                    user=ride.driver, title="Ride cancelled",
                    message="The passenger cancelled the assigned ride.",
                    notification_type=Notification.Type.DELIVERY,
                    data={"service": "RIDE", "ride_id": str(ride.pk), "status": ride.status},
                )

        ride = ride_queryset().get(pk=ride.pk)
        return Response({
            "success": True,
            "message": "Ride cancelled.",
            "data": RideSerializer(ride, context={"request": request}).data,
        })


class DriverRideListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = RideSerializer

    def get_queryset(self):
        ensure_driver(self.request.user)
        return ride_queryset().filter(
            driver=self.request.user,
            status__in=(
                Ride.Status.DRIVER_ASSIGNED,
                Ride.Status.DRIVER_ARRIVING,
                Ride.Status.IN_PROGRESS,
            ),
        )


class DriverProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        ensure_driver(request.user)
        profile = get_object_or_404(RideDriverProfile, user=request.user)
        return Response({"success": True, "data": RideDriverProfileSerializer(profile).data})

    def post(self, request):
        ensure_driver(request.user)
        if RideDriverProfile.objects.filter(user=request.user).exists():
            raise ValidationError({"profile": "Driver vehicle profile already exists; use PATCH."})
        serializer = RideDriverProfileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = serializer.save(user=request.user)
        return Response(
            {"success": True, "message": "Driver profile created.", "data": RideDriverProfileSerializer(profile).data},
            status=status.HTTP_201_CREATED,
        )

    def patch(self, request):
        ensure_driver(request.user)
        profile = get_object_or_404(RideDriverProfile, user=request.user)
        serializer = RideDriverProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        profile = serializer.save()
        return Response({"success": True, "message": "Driver profile updated.", "data": RideDriverProfileSerializer(profile).data})


class DriverLocationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ensure_driver(request.user)
        serializer = DriverLocationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            profile = get_object_or_404(
                RideDriverProfile.objects.select_for_update(), user=request.user
            )
            profile.current_latitude = serializer.validated_data["latitude"]
            profile.current_longitude = serializer.validated_data["longitude"]
            profile.last_location_at = timezone.now()
            profile.save(update_fields=[
                "current_latitude", "current_longitude", "last_location_at", "updated_at"
            ])
        return Response({
            "success": True,
            "message": "Driver location updated.",
            "data": {
                "latitude": profile.current_latitude,
                "longitude": profile.current_longitude,
                "last_location_at": profile.last_location_at,
            },
        })


class DriverAvailabilityView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ensure_driver(request.user)
        serializer = DriverAvailabilitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        desired_availability = serializer.validated_data["is_available"]

        with transaction.atomic():
            profile = get_object_or_404(
                RideDriverProfile.objects.select_for_update(), user=request.user
            )
            if desired_availability:
                if profile.is_suspended or not profile.is_approved:
                    raise PermissionDenied("Driver approval is required before going available.")
                require_fresh_driver_location(profile)
                if has_active_ride(request.user):
                    raise ValidationError(
                        {"is_available": "Complete your active ride before accepting another ride."}
                    )
            profile.is_available = desired_availability
            profile.save(update_fields=["is_available", "updated_at"])

        return Response({
            "success": True,
            "message": "Driver availability updated.",
            "data": {"is_available": profile.is_available},
        })


class AvailableRideListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        ensure_driver(request.user)
        profile = get_object_or_404(RideDriverProfile, user=request.user)
        if profile.is_suspended or not profile.is_approved:
            raise PermissionDenied("Your driver profile is not approved for dispatch.")
        if not profile.is_available:
            raise ValidationError({"is_available": "Go available to view nearby ride requests."})
        require_fresh_driver_location(profile)
        if has_active_ride(request.user):
            raise ValidationError({"ride": "Complete your active ride before viewing new requests."})

        latitude = float(profile.current_latitude)
        longitude = float(profile.current_longitude)
        latitude_delta = DRIVER_SEARCH_RADIUS_KM / 110.574
        longitude_scale = max(abs(cos(radians(latitude))), 0.1)
        longitude_delta = DRIVER_SEARCH_RADIUS_KM / (111.320 * longitude_scale)

        candidates = ride_queryset().filter(
            status__in=ACCEPTABLE_RIDE_STATUSES,
            vehicle_type=profile.vehicle_type,
            pickup_latitude__gte=Decimal(str(latitude - latitude_delta)),
            pickup_latitude__lte=Decimal(str(latitude + latitude_delta)),
            pickup_longitude__gte=Decimal(str(longitude - longitude_delta)),
            pickup_longitude__lte=Decimal(str(longitude + longitude_delta)),
        )
        nearby = []
        for ride in candidates:
            distance = haversine_distance_km(
                profile.current_latitude,
                profile.current_longitude,
                ride.pickup_latitude,
                ride.pickup_longitude,
            )
            if distance <= DRIVER_SEARCH_RADIUS_KM:
                nearby.append((distance, ride))
        nearby.sort(key=lambda item: item[0])

        data = [
            {
                "pickup_distance_km": round(distance, 2),
                "ride": RideSerializer(ride, context={"request": request}).data,
            }
            for distance, ride in nearby[:50]
        ]
        return Response({"success": True, "count": len(data), "data": data})


class AcceptRideView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        ensure_driver(request.user)
        with transaction.atomic():
            profile = get_object_or_404(
                RideDriverProfile.objects.select_for_update(), user=request.user
            )
            ride = get_object_or_404(Ride.objects.select_for_update(), pk=pk)

            if profile.is_suspended or not profile.is_approved:
                raise PermissionDenied("Your driver profile is not approved for dispatch.")
            if not profile.is_available:
                raise ValidationError({"is_available": "You must be available to accept a ride."})
            require_fresh_driver_location(profile)
            if has_active_ride(request.user):
                raise ValidationError({"ride": "You already have an active ride."})
            if ride.status not in ACCEPTABLE_RIDE_STATUSES or ride.driver_id is not None:
                raise ValidationError({"ride": "This ride is no longer available."})
            if ride.vehicle_type != profile.vehicle_type:
                raise ValidationError({"vehicle_type": "This ride requires a different vehicle type."})

            distance = haversine_distance_km(
                profile.current_latitude,
                profile.current_longitude,
                ride.pickup_latitude,
                ride.pickup_longitude,
            )
            if distance > DRIVER_SEARCH_RADIUS_KM:
                raise ValidationError({"ride": "This pickup is outside your dispatch radius."})

            ride.driver = request.user
            ride.status = Ride.Status.DRIVER_ASSIGNED
            ride.driver_assigned_at = timezone.now()
            ride.save(update_fields=["driver", "status", "driver_assigned_at", "updated_at"])
            profile.is_available = False
            profile.save(update_fields=["is_available", "updated_at"])
            RideStatusHistory.objects.create(
                ride=ride,
                status=Ride.Status.DRIVER_ASSIGNED,
                changed_by=request.user,
                note="Driver accepted ride request.",
            )
            from apps.notifications.models import Notification
            notify_after_commit(
                user=ride.passenger, title="Driver assigned",
                message="A driver has accepted your Bokku ride.",
                notification_type=Notification.Type.DELIVERY,
                data={"service": "RIDE", "ride_id": str(ride.pk), "status": ride.status},
            )

        ride = ride_queryset().get(pk=ride.pk)
        return Response({
            "success": True,
            "message": "Ride assigned to you.",
            "data": RideSerializer(ride, context={"request": request}).data,
        })


class DriverRideStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        ensure_driver(request.user)
        input_serializer = DriverRideStatusSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        requested_status = input_serializer.validated_data["status"]

        with transaction.atomic():
            ride = get_object_or_404(
                Ride.objects.select_for_update(), pk=pk, driver=request.user
            )
            expected_status = DRIVER_TRANSITIONS.get(ride.status)
            if requested_status != expected_status:
                raise ValidationError({
                    "status": f"Invalid transition from {ride.status} to {requested_status}."
                })

            ride.status = requested_status
            update_fields = ["status", "updated_at"]
            now = timezone.now()
            if requested_status == Ride.Status.IN_PROGRESS:
                ride.trip_started_at = now
                update_fields.append("trip_started_at")
            elif requested_status == Ride.Status.COMPLETED:
                ride.trip_completed_at = now
                update_fields.append("trip_completed_at")
            ride.save(update_fields=update_fields)
            RideStatusHistory.objects.create(
                ride=ride,
                status=requested_status,
                changed_by=request.user,
                note=f"Driver changed ride status to {requested_status}.",
            )
            from apps.notifications.models import Notification
            notify_after_commit(
                user=ride.passenger, title="Ride status updated",
                message=f"Your ride is now {requested_status.replace(chr(95), chr(32)).lower()}.",
                notification_type=Notification.Type.DELIVERY,
                data={"service": "RIDE", "ride_id": str(ride.pk), "status": ride.status},
            )

        ride = ride_queryset().get(pk=ride.pk)
        return Response({
            "success": True,
            "message": f"Ride status updated to {requested_status}.",
            "data": RideSerializer(ride, context={"request": request}).data,
        })
