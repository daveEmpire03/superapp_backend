from rest_framework import generics
from rest_framework.permissions import (
    IsAuthenticated,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import LoyaltyEntry
from .serializers import LoyaltyEntrySerializer
from .services import get_loyalty_balance


class LedgerView(generics.ListAPIView):
    serializer_class = LoyaltyEntrySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            LoyaltyEntry.objects.filter(user=self.request.user)
            .select_related("order")
            .order_by("-created_at")
        )


class BalanceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        balance = get_loyalty_balance(request.user)

        return Response(
            {
                "points": balance,
            }
        )
