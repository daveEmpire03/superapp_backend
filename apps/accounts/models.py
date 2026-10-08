import secrets

from django.contrib.auth.models import AbstractUser
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

from core.models import TimeStampedModel

from .managers import UserManager


def generate_customer_id():
    return f"BRK-{secrets.token_hex(4).upper()}"


class User(AbstractUser):
    class Role(models.TextChoices):
        CUSTOMER = "CUSTOMER", "Customer"
        ADMIN = "ADMIN", "Admin"
        STORE_MANAGER = "STORE_MANAGER", "Store Manager"
        STAFF = "STAFF", "Store Staff"
        RIDER = "RIDER", "Rider"

    # Public Bokku Mart customer/account identifier.
    # Django's internal primary key remains unchanged.
    customer_id = models.CharField(
        max_length=12,
        unique=True,
        db_index=True,
        default=generate_customer_id,
        editable=False,
    )

    email = models.EmailField(
        unique=True,
    )

    phone = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
    )

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CUSTOMER,
        db_index=True,
    )

    # Email verification is required after account registration.
    is_email_verified = models.BooleanField(
        default=False,
    )

    email_verified_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    # Phone verification is NOT required for account registration.
    # It will be required later before placing an order.
    is_phone_verified = models.BooleanField(
        default=False,
    )

    phone_verified_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        indexes = [
            models.Index(
                fields=["role", "is_active"],
                name="account_role_active_idx",
            ),
        ]

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip().lower()

        if self.phone == "":
            self.phone = None

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.customer_id} - {self.email}"


class VerificationCode(TimeStampedModel):
    """
    Stores temporary verification codes for Bokku Mart.

    The actual OTP must never be stored here in plain text.
    The service layer will hash the OTP before saving it.

    Supported flows:
    - Email verification after account registration.
    - Phone verification when required during checkout.
    - Forgot-password / password-reset verification.
    """

    class Purpose(models.TextChoices):
        EMAIL_VERIFICATION = (
            "EMAIL_VERIFICATION",
            "Email Verification",
        )

        PHONE_VERIFICATION = (
            "PHONE_VERIFICATION",
            "Phone Verification",
        )

        PASSWORD_RESET = (
            "PASSWORD_RESET",
            "Password Reset",
        )

    class Channel(models.TextChoices):
        EMAIL = "EMAIL", "Email"
        SMS = "SMS", "SMS"

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="verification_codes",
    )

    purpose = models.CharField(
        max_length=30,
        choices=Purpose.choices,
        db_index=True,
    )

    channel = models.CharField(
        max_length=10,
        choices=Channel.choices,
    )

    # Snapshot of the email address or phone number the OTP was sent to.
    #
    # This is important because if a user changes their email/phone,
    # an old verification code must not verify the new destination.
    destination = models.CharField(
        max_length=254,
        db_index=True,
    )

    # Store a Django password-style hash of the OTP.
    # Never store the raw 6-digit OTP.
    code_hash = models.CharField(
        max_length=255,
    )

    expires_at = models.DateTimeField()

    used_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    failed_attempts = models.PositiveSmallIntegerField(
        default=0,
    )

    max_attempts = models.PositiveSmallIntegerField(
        default=5,
        validators=[
            MinValueValidator(1),
        ],
    )

    # When a replacement OTP is issued, the old code can immediately
    # be made inactive even if it has not yet expired.
    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    class Meta:
        ordering = [
            "-created_at",
        ]

        indexes = [
            models.Index(
                fields=[
                    "user",
                    "purpose",
                    "is_active",
                ],
                name="verify_user_purpose_idx",
            ),
            models.Index(
                fields=[
                    "destination",
                    "purpose",
                    "created_at",
                ],
                name="verify_dest_created_idx",
            ),
        ]

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    @property
    def is_used(self):
        return self.used_at is not None

    @property
    def attempts_exhausted(self):
        return self.failed_attempts >= self.max_attempts

    @property
    def can_be_used(self):
        return (
            self.is_active
            and not self.is_used
            and not self.is_expired
            and not self.attempts_exhausted
        )

    def __str__(self):
        return (
            f"{self.user.customer_id} - "
            f"{self.get_purpose_display()} - "
            f"{self.destination}"
        )


class Address(TimeStampedModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="addresses",
    )

    label = models.CharField(
        max_length=50,
        default="Home",
    )

    recipient_name = models.CharField(
        max_length=150,
    )

    phone = models.CharField(
        max_length=20,
    )

    address_line = models.CharField(
        max_length=255,
    )

    city = models.CharField(
        max_length=100,
    )

    state = models.CharField(
        max_length=100,
    )

    landmark = models.CharField(
        max_length=255,
        blank=True,
    )

    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(-90),
            MaxValueValidator(90),
        ],
    )

    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(-180),
            MaxValueValidator(180),
        ],
    )

    is_default = models.BooleanField(
        default=False,
        db_index=True,
    )

    class Meta:
        ordering = [
            "-is_default",
            "-created_at",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=Q(is_default=True),
                name="unique_default_address_per_user",
            ),
        ]

        indexes = [
            models.Index(
                fields=[
                    "user",
                    "created_at",
                ],
                name="address_user_created_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.recipient_name} - "
            f"{self.address_line}, "
            f"{self.city}, "
            f"{self.state}"
        )
