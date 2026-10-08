from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import Product

from .models import Review
from .serializers import (
    ProductRatingSummarySerializer,
    ReviewEligibilitySerializer,
    ReviewSerializer,
)
from .services import (
    get_product_rating_summary,
    has_verified_purchase,
)


class MyReviewListCreateView(generics.ListCreateAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            Review.objects.filter(
                user=self.request.user,
            )
            .select_related(
                "user",
                "product",
            )
            .order_by("-created_at")
        )

    def perform_create(self, serializer):
        serializer.save(
            user=self.request.user,
            is_verified_purchase=True,
        )


class MyReviewDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Review.objects.filter(
            user=self.request.user,
        ).select_related(
            "user",
            "product",
        )

    def perform_update(self, serializer):
        serializer.save(
            user=self.request.user,
        )


class ProductReviewListView(generics.ListAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        product = get_object_or_404(
            Product,
            pk=self.kwargs["product_id"],
        )

        return (
            Review.objects.filter(
                product=product,
                is_approved=True,
            )
            .select_related(
                "user",
                "product",
            )
            .order_by("-created_at")
        )


class ProductRatingSummaryView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, product_id):
        product = get_object_or_404(
            Product,
            pk=product_id,
        )

        summary = get_product_rating_summary(product)

        serializer = ProductRatingSummarySerializer(
            {
                "product_id": product.id,
                **summary,
            }
        )

        return Response(serializer.data)


class ReviewEligibilityView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, product_id):
        product = get_object_or_404(
            Product,
            pk=product_id,
        )

        already_reviewed = Review.objects.filter(
            user=request.user,
            product=product,
        ).exists()

        eligible = not already_reviewed and has_verified_purchase(
            user=request.user,
            product=product,
        )

        serializer = ReviewEligibilitySerializer(
            {
                "product_id": product.id,
                "eligible": eligible,
                "already_reviewed": already_reviewed,
            }
        )

        return Response(serializer.data)
