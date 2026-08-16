"""
Background send worker (see architecture-plan.md milestone 5/6 and
campaigns/sending_engine.py's original docstring).

Campaigns with a small number of pending recipients are still sent inline
inside the request (see campaigns/views.py::send_campaign, gated by
settings.SYNC_SEND_THRESHOLD) for instant feedback. Larger campaigns are
just flipped to status=SENDING and left for this command to pick up, so a
single big send can't time out a web request.

Run this:
  - manually, whenever: `python manage.py send_pending_campaigns`
  - on a schedule, via a Render Cron Job (paid plans) or any external
    scheduler that can run a one-off command against this service —
    see README.md "Processing large campaigns in the background".

It's safe to run repeatedly / overlap-tolerant in the common case: each
call only touches recipients still in PENDING status, and a campaign that
finishes moves itself to COMPLETED so later runs skip it. It is NOT
safe against two instances of this command running at the exact same
time against the same campaign (no row locking) — for v1, run it as a
single scheduled job, not multiple concurrent workers.
"""
from django.core.management.base import BaseCommand

from campaigns.models import Campaign
from campaigns.sending_engine import send_campaign_now


class Command(BaseCommand):
    help = "Resume sending for all campaigns currently in status=SENDING (the background half of the send pipeline)."

    def handle(self, *args, **options):
        campaigns = Campaign.objects.filter(status=Campaign.Status.SENDING)
        count = campaigns.count()

        if not count:
            self.stdout.write("No campaigns waiting to send.")
            return

        self.stdout.write(f"Found {count} campaign(s) in SENDING status.")
        for campaign in campaigns:
            pending = campaign.recipients.filter(status="pending").count()
            self.stdout.write(f"  Campaign #{campaign.pk} “{campaign.name}” — {pending} pending recipient(s)...")
            try:
                send_campaign_now(campaign)
            except Exception as exc:  # noqa: BLE001 — one bad campaign shouldn't stop the rest
                self.stderr.write(self.style.ERROR(f"    Failed: {exc}"))
                continue
            campaign.refresh_from_db()
            self.stdout.write(self.style.SUCCESS(f"    Now {campaign.get_status_display()}."))
