from django.urls import path
from .views import InitializePaymentView,VerifyPaymentView,flutterwave_webhook
urlpatterns=[path('initialize/',InitializePaymentView.as_view()),path('verify/',VerifyPaymentView.as_view()),path('webhooks/flutterwave/',flutterwave_webhook)]
