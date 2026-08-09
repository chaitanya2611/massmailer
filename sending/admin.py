from django.contrib import admin

from .models import SendingAccount


@admin.register(SendingAccount)
class SendingAccountAdmin(admin.ModelAdmin):
    list_display = ("sender_email", "provider", "user", "status", "connected_at")
    list_filter = ("provider", "status")
    search_fields = ("sender_email", "user__username", "user__email")
    readonly_fields = ("access_token", "refresh_token", "connected_at", "updated_at")
