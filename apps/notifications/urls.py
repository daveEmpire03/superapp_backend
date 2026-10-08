from django.urls import path
from .views import DeviceTokenView,NotificationListView,ReadNotificationView
urlpatterns=[path('',NotificationListView.as_view()),path('devices/',DeviceTokenView.as_view()),path('<uuid:pk>/read/',ReadNotificationView.as_view())]
