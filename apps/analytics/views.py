from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AnalyticsEvent
from .permissions import IsAnalyticsStaff
from .serializers import (
    AnalyticsEventSerializer,
    AnalyticsPeriodQuerySerializer,
    AnalyticsStoreQuerySerializer,
)
from .services import (
    get_dashboard,
    get_delivery_performance,
    get_low_stock_data,
    get_revenue_series,
    get_store_performance,
    get_top_products,
)


class EventView(generics.CreateAPIView):
    serializer_class = AnalyticsEventSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None

        serializer.save(
            user=user,
        )


class DashboardView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsAnalyticsStaff,
    ]

    def get(self, request):
        serializer = AnalyticsPeriodQuerySerializer(
            data=request.query_params,
        )
        serializer.is_valid(
            raise_exception=True,
        )

        data = get_dashboard(
            user=request.user,
            **serializer.validated_data,
        )

        return Response(data)


class RevenueAnalyticsView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsAnalyticsStaff,
    ]

    def get(self, request):
        serializer = AnalyticsPeriodQuerySerializer(
            data=request.query_params,
        )
        serializer.is_valid(
            raise_exception=True,
        )

        data = get_revenue_series(
            user=request.user,
            **serializer.validated_data,
        )

        return Response(data)


class TopProductsView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsAnalyticsStaff,
    ]

    def get(self, request):
        serializer = AnalyticsPeriodQuerySerializer(
            data=request.query_params,
        )
        serializer.is_valid(
            raise_exception=True,
        )

        data = get_top_products(
            user=request.user,
            **serializer.validated_data,
        )

        return Response(data)


class StorePerformanceView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsAnalyticsStaff,
    ]

    def get(self, request):
        serializer = AnalyticsPeriodQuerySerializer(
            data=request.query_params,
        )
        serializer.is_valid(
            raise_exception=True,
        )

        data = get_store_performance(
            user=request.user,
            **serializer.validated_data,
        )

        return Response(data)


class LowStockAnalyticsView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsAnalyticsStaff,
    ]

    def get(self, request):
        serializer = AnalyticsStoreQuerySerializer(
            data=request.query_params,
        )
        serializer.is_valid(
            raise_exception=True,
        )

        data = get_low_stock_data(
            user=request.user,
            **serializer.validated_data,
        )

        return Response(data)


class DeliveryPerformanceView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsAnalyticsStaff,
    ]

    def get(self, request):
        serializer = AnalyticsPeriodQuerySerializer(
            data=request.query_params,
        )
        serializer.is_valid(
            raise_exception=True,
        )

        data = get_delivery_performance(
            user=request.user,
            **serializer.validated_data,
        )

        return Response(data)
