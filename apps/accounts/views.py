from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import (
    generics,
    permissions,
    status,
)
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from .models import Address
from .serializers import (
    AddressSerializer,
    BokkuTokenObtainPairSerializer,
    ChangePasswordSerializer,
    EmailVerificationSerializer,
    ForgotPasswordSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetVerifySerializer,
    RegisterSerializer,
    ResendEmailVerificationSerializer,
    UserSerializer,
)
from .services import (
    VerificationCooldownError,
    VerificationServiceError,
    request_password_reset,
    reset_password,
    send_email_verification_code,
    verify_password_reset_code,
    verify_user_email,
)


User = get_user_model()


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [
        permissions.AllowAny,
    ]

    def create(
        self,
        request,
        *args,
        **kwargs,
    ):
        serializer = self.get_serializer(
            data=request.data,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        user = serializer.save()

        email_sent = True

        try:
            send_email_verification_code(
                user,
                enforce_cooldown=False,
            )

        except Exception:
            # The account has already been safely created.
            #
            # Do not delete it just because the mail provider has
            # temporarily failed. The customer can use resend.
            email_sent = False

        response_data = {
            "message": (
                "Account created. Verify your email address."
                if email_sent
                else (
                    "Account created, but we could not send "
                    "the verification email. Please request "
                    "a new verification code."
                )
            ),
            "requires_email_verification": True,
            "email": user.email,
            "email_sent": email_sent,
            "user": UserSerializer(
                user,
            ).data,
        }

        headers = self.get_success_headers(
            serializer.data,
        )

        return Response(
            response_data,
            status=status.HTTP_201_CREATED,
            headers=headers,
        )


class VerifyEmailView(APIView):
    permission_classes = [
        permissions.AllowAny,
    ]

    def post(self, request):
        serializer = EmailVerificationSerializer(
            data=request.data,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        email = serializer.validated_data["email"]

        code = serializer.validated_data["code"]

        user = User.objects.filter(
            email__iexact=email,
            is_active=True,
        ).first()

        if user is None:
            return Response(
                {
                    "code": "invalid_verification_code",
                    "message": ("The verification code is invalid " "or expired."),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = verify_user_email(
                user=user,
                code=code,
            )

        except VerificationServiceError as exc:
            return Response(
                {
                    "code": exc.code,
                    "message": exc.message,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        refresh = RefreshToken.for_user(
            user,
        )

        return Response(
            {
                "message": ("Email verified successfully."),
                "requires_email_verification": False,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserSerializer(
                    user,
                ).data,
            },
            status=status.HTTP_200_OK,
        )


class ResendEmailVerificationView(APIView):
    permission_classes = [
        permissions.AllowAny,
    ]

    def post(self, request):
        serializer = ResendEmailVerificationSerializer(
            data=request.data,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        email = serializer.validated_data["email"]

        user = User.objects.filter(
            email__iexact=email,
            is_active=True,
        ).first()

        # Keep the response safe even if the account does not exist.
        if user is None:
            return Response(
                {
                    "message": (
                        "If the account exists and still "
                        "requires verification, a new code "
                        "has been sent."
                    )
                },
                status=status.HTTP_200_OK,
            )

        if user.is_email_verified:
            return Response(
                {
                    "message": (
                        "If the account exists and still "
                        "requires verification, a new code "
                        "has been sent."
                    )
                },
                status=status.HTTP_200_OK,
            )

        try:
            send_email_verification_code(
                user,
                enforce_cooldown=True,
            )

        except VerificationCooldownError as exc:
            return Response(
                {
                    "code": exc.code,
                    "message": exc.message,
                    "retry_after": exc.seconds,
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        except Exception:
            return Response(
                {
                    "code": "email_delivery_failed",
                    "message": (
                        "We could not send the verification "
                        "email. Please try again later."
                    ),
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(
            {"message": ("A new verification code has been sent.")},
            status=status.HTTP_200_OK,
        )


class LoginView(TokenObtainPairView):
    serializer_class = BokkuTokenObtainPairSerializer

    permission_classes = [
        permissions.AllowAny,
    ]


class RefreshTokenView(TokenRefreshView):
    permission_classes = [
        permissions.AllowAny,
    ]


class ForgotPasswordView(APIView):
    permission_classes = [
        permissions.AllowAny,
    ]

    def post(self, request):
        serializer = ForgotPasswordSerializer(
            data=request.data,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        email = serializer.validated_data["email"]

        try:
            request_password_reset(
                email,
            )

        except Exception:
            # Never reveal mail-provider or account-existence
            # information from this endpoint.
            pass

        return Response(
            {
                "message": (
                    "If an account exists for this email, "
                    "a password reset code has been sent."
                )
            },
            status=status.HTTP_200_OK,
        )


class VerifyPasswordResetCodeView(APIView):
    permission_classes = [
        permissions.AllowAny,
    ]

    def post(self, request):
        serializer = PasswordResetVerifySerializer(
            data=request.data,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        try:
            reset_token = verify_password_reset_code(
                email=(serializer.validated_data["email"]),
                code=(serializer.validated_data["code"]),
            )

        except VerificationServiceError as exc:
            return Response(
                {
                    "code": exc.code,
                    "message": exc.message,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "message": ("Verification successful."),
                "reset_token": reset_token,
            },
            status=status.HTTP_200_OK,
        )


class ResetPasswordView(APIView):
    permission_classes = [
        permissions.AllowAny,
    ]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(
            data=request.data,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        try:
            reset_password(
                reset_token=(serializer.validated_data["reset_token"]),
                new_password=(serializer.validated_data["new_password"]),
            )

        except VerificationServiceError as exc:
            return Response(
                {
                    "code": exc.code,
                    "message": exc.message,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "message": (
                    "Your password has been reset " "successfully. You can now sign in."
                )
            },
            status=status.HTTP_200_OK,
        )


class ChangePasswordView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={
                "request": request,
            },
        )

        serializer.is_valid(
            raise_exception=True,
        )

        user = request.user

        user.set_password(serializer.validated_data["new_password"])

        user.save(
            update_fields=[
                "password",
            ]
        )

        return Response(
            {"message": ("Password changed successfully.")},
            status=status.HTTP_200_OK,
        )


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer

    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get_object(self):
        return self.request.user


class AddressListCreateView(generics.ListCreateAPIView):
    serializer_class = AddressSerializer

    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get_queryset(self):
        return Address.objects.filter(
            user=self.request.user,
        )


class AddressDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AddressSerializer

    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get_queryset(self):
        return Address.objects.filter(
            user=self.request.user,
        )

    @transaction.atomic
    def destroy(
        self,
        request,
        *args,
        **kwargs,
    ):
        address = self.get_object()

        was_default = address.is_default

        address.delete()

        if was_default:
            replacement = (
                Address.objects.filter(
                    user=request.user,
                )
                .order_by("-created_at")
                .first()
            )

            if replacement:
                replacement.is_default = True

                replacement.save(
                    update_fields=[
                        "is_default",
                        "updated_at",
                    ]
                )

        return Response(
            status=(status.HTTP_204_NO_CONTENT),
        )
