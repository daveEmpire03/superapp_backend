from django.db.models import Q
from django.utils import timezone

from rest_framework import generics
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.stores.models import Store
from apps.stores.permissions import (
    ensure_store_access,
    get_managed_store_ids,
    is_platform_admin,
)

from .models import Promotion
from .serializers import (
    PromotionSerializer,
    PromotionValidationSerializer,
)
from .services import validate_promotion


STAFF_ROLES = {
    User.Role.ADMIN,
    User.Role.STORE_MANAGER,
    User.Role.STAFF,
}


def ensure_promotion_staff(user):
    if not user.is_authenticated or (
        user.role not in STAFF_ROLES and not user.is_superuser
    ):
        raise PermissionDenied("Staff access is required.")


class PromotionListView(generics.ListAPIView):
    serializer_class = PromotionSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        now = timezone.now()

        queryset = Promotion.objects.filter(
            is_active=True,
            starts_at__lte=now,
            ends_at__gte=now,
        ).select_related("store")

        store_id = self.request.query_params.get("store")

        if store_id:
            queryset = queryset.filter(Q(store__isnull=True) | Q(store_id=store_id))

        return queryset.order_by("ends_at")


class PromotionValidateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PromotionValidationSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        store = generics.get_object_or_404(
            Store,
            id=serializer.validated_data["store_id"],
            is_active=True,
        )

        promotion, discount = validate_promotion(
            code=(serializer.validated_data["code"]),
            user=request.user,
            store=store,
            subtotal=(serializer.validated_data["subtotal"]),
        )

        return Response(
            {
                "valid": True,
                "promotion": (PromotionSerializer(promotion).data),
                "discount_amount": discount,
            }
        )


class StaffPromotionListCreateView(generics.ListCreateAPIView):
    serializer_class = PromotionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        ensure_promotion_staff(self.request.user)

        queryset = Promotion.objects.select_related("store").all()

        if is_platform_admin(self.request.user):
            return queryset

        store_ids = get_managed_store_ids(self.request.user)

        return queryset.filter(store_id__in=store_ids)

    def perform_create(self, serializer):
        ensure_promotion_staff(self.request.user)

        store = serializer.validated_data.get("store")

        if is_platform_admin(self.request.user):
            serializer.save()
            return

        if store is None:
            raise PermissionDenied(
                "Only platform admins can create " "platform-wide promotions."
            )

        ensure_store_access(
            self.request.user,
            store.id,
        )

        serializer.save()


class StaffPromotionDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = PromotionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        ensure_promotion_staff(self.request.user)

        queryset = Promotion.objects.select_related("store").all()

        if is_platform_admin(self.request.user):
            return queryset

        store_ids = get_managed_store_ids(self.request.user)

        return queryset.filter(store_id__in=store_ids)

    def perform_update(self, serializer):
        promotion = self.get_object()

        new_store = serializer.validated_data.get(
            "store",
            promotion.store,
        )

        if is_platform_admin(self.request.user):
            serializer.save()
            return

        if new_store is None:
            raise PermissionDenied(
                "Only platform admins can manage " "platform-wide promotions."
            )

        ensure_store_access(
            self.request.user,
            new_store.id,
        )

        serializer.save()

    def perform_destroy(self, instance):
        if is_platform_admin(self.request.user):
            instance.delete()
            return

        if instance.store_id is None:
            raise PermissionDenied(
                "Only platform admins can delete " "platform-wide promotions."
            )

        ensure_store_access(
            self.request.user,
            instance.store_id,
        )

        instance.delete()
