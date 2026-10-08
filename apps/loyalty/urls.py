from django.urls import path

from .views import (
    BalanceView,
    LedgerView,
)


urlpatterns = [
    path(
        "",
        LedgerView.as_view(),
        name="loyalty-ledger",
    ),
    path(
        "balance/",
        BalanceView.as_view(),
        name="loyalty-balance",
    ),
]
