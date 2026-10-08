from django.db import transaction
from django.db.models import Q
from rest_framework import generics, permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.stores.permissions import (
    get_managed_store_ids,
    is_platform_admin,
)

from .models import (
    SupportMessage,
    SupportStatusHistory,
    SupportTicket,
)
from .permissions import IsSupportStaff
from .serializers import (
    StaffTicketManageSerializer,
    SupportReplyCreateSerializer,
    SupportTicketCreateSerializer,
    SupportTicketDetailSerializer,
    SupportTicketListSerializer,
)


def _ticket_queryset():
    return SupportTicket.objects.select_related(
        "user",
        "order",
        "store",
        "assigned_to",
    ).prefetch_related(
        "replies__author",
        "status_history__changed_by",
    )


class CustomerTicketListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return _ticket_queryset().filter(user=self.request.user).order_by("-created_at")

    def get_serializer_class(self):
        if self.request.method == "POST":
            return SupportTicketCreateSerializer

        return SupportTicketListSerializer


class CustomerTicketDetailView(generics.RetrieveAPIView):
    serializer_class = SupportTicketDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return _ticket_queryset().filter(
            user=self.request.user,
        )


class CustomerTicketReplyView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):
        ticket = (
            SupportTicket.objects.select_for_update()
            .filter(
                pk=pk,
                user=request.user,
            )
            .first()
        )

        if ticket is None:
            return Response(
                {"detail": "Support ticket not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if ticket.status == SupportTicket.Status.CLOSED:
            raise ValidationError(
                {
                    "detail": (
                        "This support ticket is closed. "
                        "It must be reopened before replying."
                    )
                }
            )

        serializer = SupportReplyCreateSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        SupportMessage.objects.create(
            ticket=ticket,
            author=request.user,
            message=serializer.validated_data["message"],
            is_staff_reply=False,
        )

        if ticket.status == SupportTicket.Status.RESOLVED:
            previous_status = ticket.status

            ticket.status = SupportTicket.Status.OPEN
            ticket.resolved_at = None
            ticket.closed_at = None

            ticket.save(
                update_fields=[
                    "status",
                    "resolved_at",
                    "closed_at",
                    "updated_at",
                ]
            )

            SupportStatusHistory.objects.create(
                ticket=ticket,
                from_status=previous_status,
                to_status=SupportTicket.Status.OPEN,
                changed_by=request.user,
                note="Customer replied to a resolved ticket.",
            )

        else:
            ticket.save(
                update_fields=["updated_at"],
            )

        return Response(
            {
                "detail": "Reply added successfully.",
            },
            status=status.HTTP_201_CREATED,
        )


class StaffTicketListView(generics.ListAPIView):
    serializer_class = SupportTicketListSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        IsSupportStaff,
    ]

    def get_queryset(self):
        user = self.request.user
        queryset = _ticket_queryset()

        if not is_platform_admin(user):
            store_ids = get_managed_store_ids(user)

            queryset = queryset.filter(
                store_id__in=store_ids,
            )

        ticket_status = self.request.query_params.get("status")
        priority = self.request.query_params.get("priority")
        category = self.request.query_params.get("category")
        search = self.request.query_params.get("search")

        if ticket_status:
            queryset = queryset.filter(
                status=ticket_status,
            )

        if priority:
            queryset = queryset.filter(
                priority=priority,
            )

        if category:
            queryset = queryset.filter(
                category=category,
            )

        if search:
            queryset = queryset.filter(
                Q(subject__icontains=search)
                | Q(message__icontains=search)
                | Q(user__email__icontains=search)
                | Q(user__customer_id__icontains=search)
                | Q(order__reference__icontains=search)
            )

        return queryset.order_by("-updated_at")


class StaffTicketDetailView(generics.RetrieveAPIView):
    serializer_class = SupportTicketDetailSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        IsSupportStaff,
    ]

    def get_queryset(self):
        user = self.request.user
        queryset = _ticket_queryset()

        if is_platform_admin(user):
            return queryset

        store_ids = get_managed_store_ids(user)

        return queryset.filter(
            store_id__in=store_ids,
        )


class StaffTicketReplyView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsSupportStaff,
    ]

    def _get_ticket(self, user, pk):
        queryset = SupportTicket.objects.select_for_update()

        if not is_platform_admin(user):
            store_ids = get_managed_store_ids(user)

            queryset = queryset.filter(
                store_id__in=store_ids,
            )

        return queryset.filter(pk=pk).first()

    @transaction.atomic
    def post(self, request, pk):
        ticket = self._get_ticket(
            request.user,
            pk,
        )

        if ticket is None:
            return Response(
                {"detail": "Support ticket not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if ticket.status == SupportTicket.Status.CLOSED:
            raise ValidationError(
                {
                    "detail": (
                        "Closed tickets must be reopened "
                        "before a reply can be added."
                    )
                }
            )

        serializer = SupportReplyCreateSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        SupportMessage.objects.create(
            ticket=ticket,
            author=request.user,
            message=serializer.validated_data["message"],
            is_staff_reply=True,
        )

        ticket.save(
            update_fields=["updated_at"],
        )

        return Response(
            {
                "detail": "Support reply added successfully.",
            },
            status=status.HTTP_201_CREATED,
        )


class StaffTicketManageView(generics.UpdateAPIView):
    serializer_class = StaffTicketManageSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        IsSupportStaff,
    ]

    http_method_names = [
        "patch",
        "options",
        "head",
    ]

    def get_queryset(self):
        user = self.request.user
        queryset = SupportTicket.objects.all()

        if is_platform_admin(user):
            return queryset

        store_ids = get_managed_store_ids(user)

        return queryset.filter(
            store_id__in=store_ids,
        )
