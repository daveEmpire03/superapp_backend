from django.urls import path

from .views import (
    CustomerTicketDetailView,
    CustomerTicketListCreateView,
    CustomerTicketReplyView,
    StaffTicketDetailView,
    StaffTicketListView,
    StaffTicketManageView,
    StaffTicketReplyView,
)


urlpatterns = [
    path(
        "",
        CustomerTicketListCreateView.as_view(),
        name="support-ticket-list-create",
    ),
    path(
        "<uuid:pk>/",
        CustomerTicketDetailView.as_view(),
        name="support-ticket-detail",
    ),
    path(
        "<uuid:pk>/reply/",
        CustomerTicketReplyView.as_view(),
        name="support-ticket-reply",
    ),
    path(
        "staff/tickets/",
        StaffTicketListView.as_view(),
        name="staff-support-ticket-list",
    ),
    path(
        "staff/tickets/<uuid:pk>/",
        StaffTicketDetailView.as_view(),
        name="staff-support-ticket-detail",
    ),
    path(
        "staff/tickets/<uuid:pk>/reply/",
        StaffTicketReplyView.as_view(),
        name="staff-support-ticket-reply",
    ),
    path(
        "staff/tickets/<uuid:pk>/manage/",
        StaffTicketManageView.as_view(),
        name="staff-support-ticket-manage",
    ),
]
