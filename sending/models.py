from django.conf import settings
from django.db import models

from core.fields import EncryptedTextField


class SendingAccount(models.Model):
    """
    A mailbox a user has authorized this app to send through (Gmail or
    Outlook), via OAuth. Access/refresh tokens are encrypted at rest.
    """

    class Provider(models.TextChoices):
        GOOGLE = "google", "Gmail"
        MICROSOFT = "microsoft", "Outlook / Microsoft 365"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        NEEDS_REAUTH = "needs_reauth", "Needs re-authorization"
        REVOKED = "revoked", "Revoked"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sending_accounts")
    provider = models.CharField(max_length=20, choices=Provider.choices)
    sender_email = models.EmailField()

    access_token = EncryptedTextField(blank=True, default="")
    refresh_token = EncryptedTextField(blank=True, default="")
    token_expires_at = models.DateTimeField(null=True, blank=True)
    scopes = models.TextField(blank=True, default="", help_text="Space-separated OAuth scopes granted.")

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    connected_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "provider", "sender_email"], name="unique_account_per_user"),
        ]
        ordering = ["-connected_at"]

    def __str__(self):
        return f"{self.sender_email} ({self.get_provider_display()})"

    @property
    def daily_send_limit(self):
        if self.provider == self.Provider.GOOGLE:
            return settings.GMAIL_DAILY_SEND_LIMIT
        return settings.MS365_DAILY_SEND_LIMIT
