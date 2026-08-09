from django.conf import settings
from django.db import models


class EmailTemplate(models.Model):
    """A reusable email draft with {{variable}} placeholders."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="templates")
    name = models.CharField(max_length=255)
    subject = models.CharField(max_length=998, help_text="Can include {{variables}}.")
    body = models.TextField(help_text="Plain text or simple HTML. Can include {{variables}}.")
    is_html = models.BooleanField(default=False)
    variables_used = models.JSONField(default=list, blank=True, help_text="Variable names referenced in subject/body.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.name
