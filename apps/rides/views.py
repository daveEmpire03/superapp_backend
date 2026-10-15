from django.db import transaction
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User

from .models import Ride, RideStatusHistory
from .pricing import quote_for_location_data
from .serializers import (
    RideCreateSerializer,
    RideQuoteRequestSerializer,
    RideSerializer,
)


def ensure_passenger(user):
    if user.role != User.Role.CUSTOMER:
        raise PermissionDenied("Only customer accounts can request passenger rides.")


def ride_queryset():
    return (
        Ride.objects.select_related("passenger", "driver")
        .prefetch_related("status_history", "status_history__changed_by")
    )


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

        # The server computes the fare. Any client-supplied quoted_fare or
        # payment_status field is ignored and cannot set the stored amount.
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
