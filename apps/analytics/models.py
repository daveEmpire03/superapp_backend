from django.conf import settings
from django.db import models

from core.models import TimeStampedModel


class AnalyticsEvent(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    name = models.CharField(
        max_length=100,
    )

    properties = models.JSONField(
        default=dict,
        blank=True,
    )

    def __str__(self):
        return self.name
