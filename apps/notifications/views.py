from django.utils import timezone

from rest_framework import (
    generics,
    status,
)
from rest_framework.permissions import (
    IsAuthenticated,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    DeviceToken,
    Notification,
)
from .serializers import (
    DeviceTokenSerializer,
    NotificationSerializer,
)


class DeviceTokenView(generics.CreateAPIView):
    serializer_class = DeviceTokenSerializer
    permission_classes = [IsAuthenticated]

    def create(
        self,
        request,
        *args,
        **kwargs,
    ):
        serializer = self.get_serializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        device, created = DeviceToken.objects.update_or_create(
            token=(serializer.validated_data["token"]),
            defaults={
                "user": request.user,
                "platform": (serializer.validated_data["platform"]),
                "is_active": True,
            },
        )

        response_serializer = self.get_serializer(device)

        return Response(
            response_serializer.data,
            status=(status.HTTP_201_CREATED if created else status.HTTP_200_OK),
        )


class DeviceTokenDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(
        self,
        request,
        pk,
    ):
        try:
            device = DeviceToken.objects.get(
                pk=pk,
                user=request.user,
            )

        except DeviceToken.DoesNotExist:
            return Response(
                {"detail": "Device token not found."},
                status=(status.HTTP_404_NOT_FOUND),
            )

        # Keep the token record for operational
        # history but stop sending pushes to it.
        device.is_active = False

        device.save(
            update_fields=[
                "is_active",
                "updated_at",
            ]
        )

        return Response(status=status.HTTP_204_NO_CONTENT)


class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Notification.objects.filter(user=self.request.user).order_by(
            "-created_at"
        )

        unread = self.request.query_params.get("unread")

        if unread in {
            "1",
            "true",
            "True",
        }:
            queryset = queryset.filter(is_read=False)

        return queryset


class NotificationUnreadCountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        count = Notification.objects.filter(
            user=request.user,
            is_read=False,
        ).count()

        return Response(
            {
                "unread_count": count,
            }
        )


class ReadNotificationView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(
        self,
        request,
        pk,
    ):
        try:
            notification = Notification.objects.get(
                pk=pk,
                user=request.user,
            )

        except Notification.DoesNotExist:
            return Response(
                {"detail": "Notification not found."},
                status=(status.HTTP_404_NOT_FOUND),
            )

        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()

            notification.save(
                update_fields=[
                    "is_read",
                    "read_at",
                    "updated_at",
                ]
            )

        return Response(NotificationSerializer(notification).data)


class ReadAllNotificationsView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        now = timezone.now()

        updated = Notification.objects.filter(
            user=request.user,
            is_read=False,
        ).update(
            is_read=True,
            read_at=now,
            updated_at=now,
        )

        return Response(
            {
                "updated": updated,
            }
        )
