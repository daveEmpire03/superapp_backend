from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from apps.orders.models import Order
from apps.stores.models import Store, StoreStaffMembership
from apps.stores.permissions import is_platform_admin

from .models import (
    SupportMessage,
    SupportStatusHistory,
    SupportTicket,
)

User = get_user_model()


class SupportMessageSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = SupportMessage
        fields = (
            "id",
            "author_name",
            "message",
            "is_staff_reply",
            "created_at",
        )

        read_only_fields = fields

    def get_author_name(self, obj):
        if obj.author is None:
            return "Bokku Support"

        if obj.is_staff_reply:
            return "Bokku Support"

        full_name = obj.author.get_full_name().strip()

        if full_name:
            return full_name

        return "Customer"


class SupportStatusHistorySerializer(serializers.ModelSerializer):
    changed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = SupportStatusHistory
        fields = (
            "id",
            "from_status",
            "to_status",
            "changed_by_name",
            "note",
            "created_at",
        )

        read_only_fields = fields

    def get_changed_by_name(self, obj):
        if obj.changed_by is None:
            return "System"

        if obj.changed_by_id == obj.ticket.user_id:
            return "Customer"

        return "Bokku Support"


class SupportTicketListSerializer(serializers.ModelSerializer):
    order_reference = serializers.CharField(
        source="order.reference",
        read_only=True,
    )

    store_name = serializers.CharField(
        source="store.name",
        read_only=True,
    )

    assigned_to_email = serializers.EmailField(
        source="assigned_to.email",
        read_only=True,
    )

    class Meta:
        model = SupportTicket

        fields = (
            "id",
            "category",
            "priority",
            "subject",
            "status",
            "order_reference",
            "store_name",
            "assigned_to_email",
            "created_at",
            "updated_at",
        )

        read_only_fields = fields


class SupportTicketDetailSerializer(serializers.ModelSerializer):
    customer_id = serializers.CharField(
        source="user.customer_id",
        read_only=True,
    )

    customer_email = serializers.EmailField(
        source="user.email",
        read_only=True,
    )

    customer_name = serializers.SerializerMethodField()

    order_reference = serializers.CharField(
        source="order.reference",
        read_only=True,
    )

    store_name = serializers.CharField(
        source="store.name",
        read_only=True,
    )

    assigned_to_email = serializers.EmailField(
        source="assigned_to.email",
        read_only=True,
    )

    replies = SupportMessageSerializer(
        many=True,
        read_only=True,
    )

    status_history = SupportStatusHistorySerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = SupportTicket

        fields = (
            "id",
            "customer_id",
            "customer_email",
            "customer_name",
            "category",
            "priority",
            "subject",
            "message",
            "status",
            "order",
            "order_reference",
            "store",
            "store_name",
            "assigned_to_email",
            "resolved_at",
            "closed_at",
            "replies",
            "status_history",
            "created_at",
            "updated_at",
        )

        read_only_fields = fields

    def get_customer_name(self, obj):
        full_name = obj.user.get_full_name().strip()

        if full_name:
            return full_name

        return "Bokku Customer"


class SupportTicketCreateSerializer(serializers.ModelSerializer):
    order = serializers.PrimaryKeyRelatedField(
        queryset=Order.objects.all(),
        required=False,
        allow_null=True,
    )

    store = serializers.PrimaryKeyRelatedField(
        queryset=Store.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = SupportTicket

        fields = (
            "id",
            "category",
            "order",
            "store",
            "subject",
            "message",
            "status",
            "priority",
            "created_at",
        )

        read_only_fields = (
            "id",
            "status",
            "priority",
            "created_at",
        )

    def validate_subject(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError("Subject is required.")

        return value

    def validate_message(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError("Message is required.")

        return value

    def validate(self, attrs):
        request = self.context["request"]

        order = attrs.get("order")
        store = attrs.get("store")

        if order is not None:
            if order.user_id != request.user.id:
                raise serializers.ValidationError(
                    {
                        "order": (
                            "You can only create a support ticket "
                            "for your own order."
                        )
                    }
                )

            if store is not None and store.id != order.store_id:
                raise serializers.ValidationError(
                    {
                        "store": (
                            "The selected store does not match " "the order's store."
                        )
                    }
                )

            attrs["store"] = order.store

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        request = self.context["request"]

        ticket = SupportTicket.objects.create(
            user=request.user,
            **validated_data,
        )

        SupportStatusHistory.objects.create(
            ticket=ticket,
            from_status="",
            to_status=SupportTicket.Status.OPEN,
            changed_by=request.user,
            note="Support ticket created.",
        )

        return ticket


class SupportReplyCreateSerializer(serializers.Serializer):
    message = serializers.CharField(
        max_length=5000,
        trim_whitespace=True,
    )

    def validate_message(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError("Reply message is required.")

        return value


class StaffTicketManageSerializer(serializers.ModelSerializer):
    note = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        write_only=True,
    )

    assigned_to = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = SupportTicket

        fields = (
            "status",
            "priority",
            "assigned_to",
            "note",
        )

    def validate_status(self, value):
        if self.instance is None:
            return value

        current = self.instance.status

        if value == current:
            return value

        transitions = {
            SupportTicket.Status.OPEN: {
                SupportTicket.Status.IN_PROGRESS,
                SupportTicket.Status.RESOLVED,
                SupportTicket.Status.CLOSED,
            },
            SupportTicket.Status.IN_PROGRESS: {
                SupportTicket.Status.WAITING_CUSTOMER,
                SupportTicket.Status.RESOLVED,
                SupportTicket.Status.CLOSED,
            },
            SupportTicket.Status.WAITING_CUSTOMER: {
                SupportTicket.Status.IN_PROGRESS,
                SupportTicket.Status.RESOLVED,
                SupportTicket.Status.CLOSED,
            },
            SupportTicket.Status.RESOLVED: {
                SupportTicket.Status.OPEN,
                SupportTicket.Status.CLOSED,
            },
            SupportTicket.Status.CLOSED: {
                SupportTicket.Status.OPEN,
            },
        }

        if value not in transitions.get(current, set()):
            raise serializers.ValidationError(
                f"Cannot change support ticket from " f"{current} to {value}."
            )

        return value

    def validate_assigned_to(self, user):
        if user is None:
            return None

        ticket = self.instance

        if ticket is None:
            return user

        if is_platform_admin(user):
            return user

        if ticket.store_id is None:
            raise serializers.ValidationError(
                "Platform-wide tickets can only be assigned "
                "to platform administrators."
            )

        membership_exists = StoreStaffMembership.objects.filter(
            user=user,
            store_id=ticket.store_id,
            is_active=True,
        ).exists()

        if not membership_exists:
            raise serializers.ValidationError(
                "The selected staff member does not manage " "this ticket's store."
            )

        return user

    @transaction.atomic
    def update(self, instance, validated_data):
        request = self.context["request"]

        note = validated_data.pop("note", "")

        previous_status = instance.status
        new_status = validated_data.get(
            "status",
            previous_status,
        )

        instance = super().update(
            instance,
            validated_data,
        )

        if new_status != previous_status:
            if new_status == SupportTicket.Status.RESOLVED:
                instance.resolved_at = timezone.now()

            elif new_status == SupportTicket.Status.CLOSED:
                instance.closed_at = timezone.now()

            elif new_status == SupportTicket.Status.OPEN:
                instance.resolved_at = None
                instance.closed_at = None

            instance.save(
                update_fields=[
                    "resolved_at",
                    "closed_at",
                    "updated_at",
                ]
            )

            SupportStatusHistory.objects.create(
                ticket=instance,
                from_status=previous_status,
                to_status=new_status,
                changed_by=request.user,
                note=note,
            )

        return instance
