from django.contrib import admin

from .models import EmailTemplate


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "is_html", "updated_at")
    search_fields = ("name", "subject", "user__username")
