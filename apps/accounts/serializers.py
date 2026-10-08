from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Address


User = get_user_model()


def split_full_name(full_name):
    """
    Convert a customer-facing full name into Django's first_name/last_name
    fields without changing the User model structure.
    """
    parts = full_name.strip().split()

    if not parts:
        return "", ""

    first_name = parts[0]
    last_name = " ".join(parts[1:])

    return first_name, last_name


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User

        fields = (
            "customer_id",
            "email",
            "phone",
            "first_name",
            "last_name",
            "full_name",
            "role",
            "is_email_verified",
            "email_verified_at",
            "is_phone_verified",
            "phone_verified_at",
        )

        read_only_fields = (
            "customer_id",
            "email",
            "full_name",
            "role",
            "is_email_verified",
            "email_verified_at",
            "is_phone_verified",
            "phone_verified_at",
        )

    def get_full_name(self, obj):
        return obj.get_full_name().strip()


class RegisterSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(
        write_only=True,
        max_length=300,
    )

    password = serializers.CharField(
        write_only=True,
        min_length=8,
        trim_whitespace=False,
        style={
            "input_type": "password",
        },
    )

    class Meta:
        model = User

        fields = (
            "customer_id",
            "email",
            "phone",
            "full_name",
            "password",
        )

        read_only_fields = ("customer_id",)

    def validate_email(self, value):
        email = value.strip().lower()

        if User.objects.filter(
            email__iexact=email,
        ).exists():
            raise serializers.ValidationError(
                "An account with this email already exists."
            )

        return email

    def validate_phone(self, value):
        if value is None:
            return None

        phone = value.strip()

        if not phone:
            return None

        if User.objects.filter(
            phone=phone,
        ).exists():
            raise serializers.ValidationError(
                "An account with this phone number already exists."
            )

        return phone

    def validate_full_name(self, value):
        full_name = " ".join(value.strip().split())

        if len(full_name) < 2:
            raise serializers.ValidationError("Enter your full name.")

        return full_name

    def validate_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages)) from exc

        return value

    def create(self, validated_data):
        password = validated_data.pop(
            "password",
        )

        full_name = validated_data.pop(
            "full_name",
        )

        first_name, last_name = split_full_name(
            full_name,
        )

        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    password=password,
                    role=User.Role.CUSTOMER,
                    first_name=first_name,
                    last_name=last_name,
                    is_email_verified=False,
                    is_phone_verified=False,
                    **validated_data,
                )

        except IntegrityError as exc:
            raise serializers.ValidationError(
                {"detail": ("An account with the supplied details " "already exists.")}
            ) from exc

        return user


class EmailVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()

    code = serializers.RegexField(
        regex=r"^\d{6}$",
        error_messages={
            "invalid": "Enter the 6-digit verification code.",
        },
    )

    def validate_email(self, value):
        return value.strip().lower()


class ResendEmailVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        return value.strip().lower()


class ForgotPasswordSerializer(serializers.Serializer):
    """
    Do not check whether the email exists here.

    The forgot-password endpoint should return the same response whether
    the email exists or not to avoid account enumeration.
    """

    email = serializers.EmailField()

    def validate_email(self, value):
        return value.strip().lower()


class PasswordResetVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()

    code = serializers.RegexField(
        regex=r"^\d{6}$",
        error_messages={
            "invalid": "Enter the 6-digit verification code.",
        },
    )

    def validate_email(self, value):
        return value.strip().lower()


class PasswordResetConfirmSerializer(serializers.Serializer):
    """
    After the password-reset OTP is verified, the backend service will
    issue a short-lived reset token.

    The raw OTP does not need to be sent again when changing the password.
    """

    reset_token = serializers.CharField(
        write_only=True,
    )

    new_password = serializers.CharField(
        write_only=True,
        min_length=8,
        trim_whitespace=False,
        style={
            "input_type": "password",
        },
    )

    confirm_password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        style={
            "input_type": "password",
        },
    )

    def validate(self, attrs):
        new_password = attrs.get(
            "new_password",
        )

        confirm_password = attrs.get(
            "confirm_password",
        )

        if new_password != confirm_password:
            raise serializers.ValidationError(
                {"confirm_password": ("Passwords do not match.")}
            )

        try:
            validate_password(
                new_password,
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError(
                {"new_password": list(exc.messages)}
            ) from exc

        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        style={
            "input_type": "password",
        },
    )

    new_password = serializers.CharField(
        write_only=True,
        min_length=8,
        trim_whitespace=False,
        style={
            "input_type": "password",
        },
    )

    confirm_password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        style={
            "input_type": "password",
        },
    )

    def validate_current_password(self, value):
        user = self.context["request"].user

        if not user.check_password(value):
            raise serializers.ValidationError("Your current password is incorrect.")

        return value

    def validate(self, attrs):
        new_password = attrs.get(
            "new_password",
        )

        confirm_password = attrs.get(
            "confirm_password",
        )

        if new_password != confirm_password:
            raise serializers.ValidationError(
                {"confirm_password": ("Passwords do not match.")}
            )

        request = self.context.get(
            "request",
        )

        user = request.user if request is not None else None

        try:
            validate_password(
                new_password,
                user=user,
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError(
                {"new_password": list(exc.messages)}
            ) from exc

        return attrs


class PhoneVerificationSerializer(serializers.Serializer):
    """
    Phone verification is performed later for authenticated customers,
    normally when checkout requires a verified phone number.
    """

    code = serializers.RegexField(
        regex=r"^\d{6}$",
        error_messages={
            "invalid": "Enter the 6-digit verification code.",
        },
    )


class BokkuTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        if attrs.get("email"):
            attrs["email"] = attrs["email"].strip().lower()

        data = super().validate(
            attrs,
        )

        if not self.user.is_email_verified:
            raise serializers.ValidationError(
                {
                    "code": ("email_verification_required"),
                    "message": (
                        "Please verify your email address " "before signing in."
                    ),
                    "requires_email_verification": True,
                    "email": self.user.email,
                }
            )

        data["user"] = UserSerializer(
            self.user,
        ).data

        return data


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address

        fields = (
            "id",
            "label",
            "recipient_name",
            "phone",
            "address_line",
            "city",
            "state",
            "landmark",
            "latitude",
            "longitude",
            "is_default",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):
        latitude = attrs.get(
            "latitude",
            getattr(
                self.instance,
                "latitude",
                None,
            ),
        )

        longitude = attrs.get(
            "longitude",
            getattr(
                self.instance,
                "longitude",
                None,
            ),
        )

        if (latitude is None) != (longitude is None):
            raise serializers.ValidationError(
                {
                    "location": (
                        "Latitude and longitude must either "
                        "both be provided or both be omitted."
                    )
                }
            )

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        user = self.context["request"].user

        has_addresses = Address.objects.filter(
            user=user,
        ).exists()

        if not has_addresses:
            validated_data["is_default"] = True

        elif validated_data.get("is_default"):
            Address.objects.filter(
                user=user,
                is_default=True,
            ).update(
                is_default=False,
            )

        return Address.objects.create(
            user=user,
            **validated_data,
        )

    @transaction.atomic
    def update(
        self,
        instance,
        validated_data,
    ):
        user = self.context["request"].user

        make_default = validated_data.get(
            "is_default",
            instance.is_default,
        )

        if make_default:
            Address.objects.filter(
                user=user,
                is_default=True,
            ).exclude(
                pk=instance.pk,
            ).update(
                is_default=False,
            )

        elif instance.is_default and validated_data.get("is_default") is False:
            other_address = (
                Address.objects.filter(
                    user=user,
                )
                .exclude(
                    pk=instance.pk,
                )
                .order_by("-created_at")
                .first()
            )

            if other_address:
                other_address.is_default = True
                other_address.save(
                    update_fields=[
                        "is_default",
                        "updated_at",
                    ]
                )

            else:
                validated_data["is_default"] = True

        return super().update(
            instance,
            validated_data,
        )
