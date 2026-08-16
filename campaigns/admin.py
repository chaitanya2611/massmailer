from datetime import timedelta

from django.conf import settings
from django.contrib import admin
from django.utils import timezone

from .models import Campaign, CampaignRecipient, UnsubscribeEntry


class CampaignRecipientInline(admin.TabularInline):
    model = CampaignRecipient
    extra = 0
    readonly_fields = ("row_data", "resolved_email", "status", "error_message", "sent_at")
    can_delete = False
    max_num = 0


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "status", "created_at", "started_at", "completed_at", "sent_last_24h", "high_volume")
    list_filter = ("status",)
    search_fields = ("name", "user__username")
    inlines = [CampaignRecipientInline]

    @admin.display(description="Sent (24h, this user)")
    def sent_last_24h(self, obj):
        cutoff = timezone.now() - timedelta(hours=24)
        return CampaignRecipient.objects.filter(
            campaign__user=obj.user, status=CampaignRecipient.Status.SENT, sent_at__gte=cutoff
        ).count()

    @admin.display(description="High volume?", boolean=True)
    def high_volume(self, obj):
        """Flags accounts sending more than SUSPICIOUS_DAILY_SEND_THRESHOLD
        in a day for manual review — doesn't block sending. See
        architecture-plan.md section 6 (compliance & abuse prevention)."""
        return self.sent_last_24h(obj) > settings.SUSPICIOUS_DAILY_SEND_THRESHOLD


@admin.register(UnsubscribeEntry)
class UnsubscribeEntryAdmin(admin.ModelAdmin):
    list_display = ("email", "user", "unsubscribed_at")
    search_fields = ("email", "user__username")
