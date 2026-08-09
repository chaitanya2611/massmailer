from django.contrib import admin

from .models import Campaign, CampaignRecipient, UnsubscribeEntry


class CampaignRecipientInline(admin.TabularInline):
    model = CampaignRecipient
    extra = 0
    readonly_fields = ("row_data", "resolved_email", "status", "error_message", "sent_at")
    can_delete = False
    max_num = 0


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "status", "created_at", "started_at", "completed_at")
    list_filter = ("status",)
    search_fields = ("name", "user__username")
    inlines = [CampaignRecipientInline]


@admin.register(UnsubscribeEntry)
class UnsubscribeEntryAdmin(admin.ModelAdmin):
    list_display = ("email", "user", "unsubscribed_at")
    search_fields = ("email", "user__username")
