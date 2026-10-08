import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, make_password
from django.core import signing
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from .models import VerificationCode


User = get_user_model()


OTP_EXPIRY_MINUTES = 10
OTP_RESEND_COOLDOWN_SECONDS = 60
OTP_MAX_ATTEMPTS = 5

PASSWORD_RESET_TOKEN_MAX_AGE_SECONDS = 10 * 60
PASSWORD_RESET_TOKEN_SALT = "bokku-mart-password-reset"


class VerificationServiceError(Exception):
    def __init__(self, message, code="verification_error"):
        self.message = message
        self.code = code

        super().__init__(message)


class VerificationCooldownError(VerificationServiceError):
    def __init__(self, seconds):
        self.seconds = seconds

        super().__init__(
            message=(
                f"Please wait {seconds} seconds before requesting "
                "another verification code."
            ),
            code="verification_cooldown",
        )


def _generate_otp():
    """
    Generate a cryptographically secure six-digit OTP.

    Leading zeroes are preserved.
    """
    return f"{secrets.randbelow(1_000_000):06d}"


def _normalise_destination(destination):
    return destination.strip().lower()


def _check_resend_cooldown(
    *,
    user,
    purpose,
    destination,
):
    latest = (
        VerificationCode.objects.filter(
            user=user,
            purpose=purpose,
            destination=destination,
        )
        .order_by("-created_at")
        .first()
    )

    if latest is None:
        return

    elapsed = (timezone.now() - latest.created_at).total_seconds()

    remaining = OTP_RESEND_COOLDOWN_SECONDS - int(elapsed)

    if remaining > 0:
        raise VerificationCooldownError(
            seconds=remaining,
        )


@transaction.atomic
def create_verification_code(
    *,
    user,
    purpose,
    channel,
    destination,
    enforce_cooldown=True,
):
    destination = _normalise_destination(
        destination,
    )

    if enforce_cooldown:
        _check_resend_cooldown(
            user=user,
            purpose=purpose,
            destination=destination,
        )

    VerificationCode.objects.filter(
        user=user,
        purpose=purpose,
        is_active=True,
    ).update(
        is_active=False,
    )

    raw_code = _generate_otp()

    verification = VerificationCode.objects.create(
        user=user,
        purpose=purpose,
        channel=channel,
        destination=destination,
        code_hash=make_password(
            raw_code,
        ),
        expires_at=timezone.now()
        + timedelta(
            minutes=OTP_EXPIRY_MINUTES,
        ),
        max_attempts=OTP_MAX_ATTEMPTS,
        is_active=True,
    )

    return verification, raw_code


def send_email_verification_code(
    user,
    *,
    enforce_cooldown=True,
):
    verification, raw_code = create_verification_code(
        user=user,
        purpose=(VerificationCode.Purpose.EMAIL_VERIFICATION),
        channel=(VerificationCode.Channel.EMAIL),
        destination=user.email,
        enforce_cooldown=enforce_cooldown,
    )

    send_mail(
        subject="Verify your Bokku Mart account",
        message=(
            f"Your Bokku Mart verification code is "
            f"{raw_code}.\n\n"
            f"This code expires in "
            f"{OTP_EXPIRY_MINUTES} minutes.\n\n"
            "If you did not create a Bokku Mart "
            "account, you can ignore this email."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[
            user.email,
        ],
        fail_silently=False,
    )

    return verification


@transaction.atomic
def verify_code(
    *,
    user,
    purpose,
    destination,
    raw_code,
):
    destination = _normalise_destination(
        destination,
    )

    verification = (
        VerificationCode.objects.select_for_update()
        .filter(
            user=user,
            purpose=purpose,
            destination=destination,
            is_active=True,
        )
        .order_by("-created_at")
        .first()
    )

    if verification is None:
        raise VerificationServiceError(
            "The verification code is invalid or no longer active.",
            code="invalid_verification_code",
        )

    if verification.is_used:
        verification.is_active = False
        verification.save(
            update_fields=[
                "is_active",
                "updated_at",
            ]
        )

        raise VerificationServiceError(
            "This verification code has already been used.",
            code="verification_code_used",
        )

    if verification.is_expired:
        verification.is_active = False
        verification.save(
            update_fields=[
                "is_active",
                "updated_at",
            ]
        )

        raise VerificationServiceError(
            "This verification code has expired.",
            code="verification_code_expired",
        )

    if verification.attempts_exhausted:
        verification.is_active = False
        verification.save(
            update_fields=[
                "is_active",
                "updated_at",
            ]
        )

        raise VerificationServiceError(
            "Too many incorrect attempts. Request a new code.",
            code="verification_attempts_exhausted",
        )

    if not check_password(
        raw_code,
        verification.code_hash,
    ):
        verification.failed_attempts += 1

        if verification.attempts_exhausted:
            verification.is_active = False

        verification.save(
            update_fields=[
                "failed_attempts",
                "is_active",
                "updated_at",
            ]
        )

        if verification.attempts_exhausted:
            raise VerificationServiceError(
                "Too many incorrect attempts. Request a new code.",
                code="verification_attempts_exhausted",
            )

        raise VerificationServiceError(
            "The verification code is incorrect.",
            code="invalid_verification_code",
        )

    verification.used_at = timezone.now()
    verification.is_active = False

    verification.save(
        update_fields=[
            "used_at",
            "is_active",
            "updated_at",
        ]
    )

    return verification


@transaction.atomic
def verify_user_email(
    *,
    user,
    code,
):
    if user.is_email_verified:
        return user

    verify_code(
        user=user,
        purpose=(VerificationCode.Purpose.EMAIL_VERIFICATION),
        destination=user.email,
        raw_code=code,
    )

    user.is_email_verified = True
    user.email_verified_at = timezone.now()

    user.save(
        update_fields=[
            "is_email_verified",
            "email_verified_at",
        ]
    )

    return user


def request_password_reset(
    email,
):
    """
    Always return normally.

    The caller must not reveal whether the supplied email belongs
    to a Bokku Mart account.
    """
    email = email.strip().lower()

    user = User.objects.filter(
        email__iexact=email,
        is_active=True,
    ).first()

    if user is None:
        return

    try:
        verification, raw_code = create_verification_code(
            user=user,
            purpose=(VerificationCode.Purpose.PASSWORD_RESET),
            channel=(VerificationCode.Channel.EMAIL),
            destination=user.email,
            enforce_cooldown=True,
        )

    except VerificationCooldownError:
        # Keep the public response generic.
        return

    send_mail(
        subject="Reset your Bokku Mart password",
        message=(
            f"Your Bokku Mart password reset code is "
            f"{raw_code}.\n\n"
            f"This code expires in "
            f"{OTP_EXPIRY_MINUTES} minutes.\n\n"
            "If you did not request a password reset, "
            "you can ignore this email."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[
            user.email,
        ],
        fail_silently=False,
    )

    return verification


def verify_password_reset_code(
    *,
    email,
    code,
):
    email = email.strip().lower()

    user = User.objects.filter(
        email__iexact=email,
        is_active=True,
    ).first()

    if user is None:
        raise VerificationServiceError(
            "The verification code is invalid or expired.",
            code="invalid_verification_code",
        )

    verify_code(
        user=user,
        purpose=(VerificationCode.Purpose.PASSWORD_RESET),
        destination=user.email,
        raw_code=code,
    )

    payload = {
        "user_id": user.pk,
        "password_hash": user.password,
    }

    return signing.dumps(
        payload,
        salt=PASSWORD_RESET_TOKEN_SALT,
        compress=True,
    )


def get_password_reset_user(
    reset_token,
):
    try:
        payload = signing.loads(
            reset_token,
            salt=PASSWORD_RESET_TOKEN_SALT,
            max_age=(PASSWORD_RESET_TOKEN_MAX_AGE_SECONDS),
        )

    except signing.SignatureExpired as exc:
        raise VerificationServiceError(
            "The password reset session has expired.",
            code="password_reset_token_expired",
        ) from exc

    except signing.BadSignature as exc:
        raise VerificationServiceError(
            "The password reset session is invalid.",
            code="invalid_password_reset_token",
        ) from exc

    user = User.objects.filter(
        pk=payload.get("user_id"),
        is_active=True,
    ).first()

    if user is None:
        raise VerificationServiceError(
            "The password reset session is invalid.",
            code="invalid_password_reset_token",
        )

    if user.password != payload.get("password_hash"):
        raise VerificationServiceError(
            "This password reset session has already been used.",
            code="password_reset_token_used",
        )

    return user


@transaction.atomic
def reset_password(
    *,
    reset_token,
    new_password,
):
    user = get_password_reset_user(
        reset_token,
    )

    user.set_password(
        new_password,
    )

    user.save(
        update_fields=[
            "password",
        ]
    )

    VerificationCode.objects.filter(
        user=user,
        purpose=(VerificationCode.Purpose.PASSWORD_RESET),
        is_active=True,
    ).update(
        is_active=False,
    )

    return user
