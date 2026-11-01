from django.urls import path
from .views import (
    DeviceTokenDeleteView,
    DeviceTokenView,
    NotificationListView,
    NotificationUnreadCountView,
    ReadAllNotificationsView,
    ReadNotificationView,
)

urlpatterns = [
    path('', NotificationListView.as_view(), name='notification-list'),
    path('unread-count/', NotificationUnreadCountView.as_view(), name='notification-unread-count'),
    path('read-all/', ReadAllNotificationsView.as_view(), name='notification-read-all'),
    path('devices/', DeviceTokenView.as_view(), name='device-token-create'),
    path('devices/<uuid:pk>/', DeviceTokenDeleteView.as_view(), name='device-token-delete'),
    path('<uuid:pk>/read/', ReadNotificationView.as_view(), name='notification-read'),
]
