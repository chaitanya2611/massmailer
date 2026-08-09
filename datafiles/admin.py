from django.contrib import admin

from .models import DataFile


@admin.register(DataFile)
class DataFileAdmin(admin.ModelAdmin):
    list_display = ("original_filename", "user", "row_count", "uploaded_at")
    search_fields = ("original_filename", "user__username")
    readonly_fields = ("columns", "row_count", "detected_email_column", "uploaded_at")
