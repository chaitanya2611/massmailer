from django.conf import settings
from django.db import models


def upload_path(instance, filename):
    return f"datafiles/user_{instance.user_id}/{filename}"


class DataFile(models.Model):
    """A CSV/Excel file a user uploaded, parsed into a list of column names."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="data_files")
    original_filename = models.CharField(max_length=255)
    file = models.FileField(upload_to=upload_path)
    columns = models.JSONField(default=list, help_text="Ordered list of column headers detected in the file.")
    row_count = models.PositiveIntegerField(default=0)
    detected_email_column = models.CharField(max_length=255, blank=True, default="")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.original_filename} ({self.row_count} rows)"
