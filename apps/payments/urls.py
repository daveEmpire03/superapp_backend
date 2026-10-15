from django.urls import path

from .views import (
    InitializePaymentView,
    InitializeServicePaymentView,
    VerifyPaymentView,
    VerifyServicePaymentView,
    flutterwave_webhook,
)


urlpatterns = [
    path("initialize/", InitializePaymentView.as_view(), name="payment-initialize"),
    path("verify/", VerifyPaymentView.as_view(), name="payment-verify"),
    path("services/initialize/", InitializeServicePaymentView.as_view(), name="service-payment-initialize"),
    path("services/verify/", VerifyServicePaymentView.as_view(), name="service-payment-verify"),
    path("webhooks/flutterwave/", flutterwave_webhook, name="flutterwave-webhook"),
]
