from django.conf import settings
from django.db import models


class Campaign(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENDING = "sending", "Sending"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="campaigns")
    name = models.CharField(max_length=255)
    template = models.ForeignKey("emailtemplates.EmailTemplate", on_delete=models.PROTECT, related_name="campaigns")
    data_file = models.ForeignKey("datafiles.DataFile", on_delete=models.PROTECT, related_name="campaigns")
    sending_account = models.ForeignKey(
        "sending.SendingAccount", on_delete=models.PROTECT, related_name="campaigns", null=True, blank=True
    )
    email_column = models.CharField(max_length=255, help_text="Column in the data file mapped to recipient email.")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class CampaignRecipient(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"
        SKIPPED = "skipped", "Skipped"

    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="recipients")
    row_data = models.JSONField(help_text="The source row, keyed by column name.")
    resolved_email = models.EmailField(blank=True, default="")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    error_message = models.TextField(blank=True, default="")
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.resolved_email or '(no email)'} — {self.status}"


class UnsubscribeEntry(models.Model):
    """
    Per-sender-user unsubscribe list. Since sends go out through the user's
    own Gmail/Outlook (not a provider with built-in suppression), the app
    maintains this list itself and excludes matching addresses at send time.
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="unsubscribes")
    email = models.EmailField()
    unsubscribed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "email"], name="unique_unsubscribe_per_user"),
        ]
        verbose_name_plural = "Unsubscribe entries"

    def __str__(self):
        return self.email
