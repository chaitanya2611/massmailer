import json

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import CampaignCreateForm
from .models import Campaign, CampaignRecipient, UnsubscribeEntry
from .sending_engine import build_recipients, send_campaign_now
from .tokens import read_unsubscribe_token


@login_required
def dashboard(request):
    user = request.user
    campaigns = user.campaigns.all()
    recent_campaigns = campaigns[:8]

    has_data_file = user.data_files.exists()
    has_template = user.templates.exists()
    has_sending_account = user.sending_accounts.filter(status="active").exists()
    has_campaign = campaigns.exists()

    stats = {
        "data_files": user.data_files.count(),
        "templates": user.templates.count(),
        "sending_accounts": user.sending_accounts.filter(status="active").count(),
        "campaigns": campaigns.count(),
        "sent_total": CampaignRecipient.objects.filter(campaign__user=user, status=CampaignRecipient.Status.SENT).count(),
        "failed_total": CampaignRecipient.objects.filter(campaign__user=user, status=CampaignRecipient.Status.FAILED).count(),
    }

    onboarding_steps = [
        {"label": "Upload a data file", "done": has_data_file, "url": "datafiles:upload"},
        {"label": "Draft an email template", "done": has_template, "url": "emailtemplates:create"},
        {"label": "Connect a Gmail or Outlook account", "done": has_sending_account, "url": "sending:list"},
        {"label": "Create your first campaign", "done": has_campaign, "url": "campaigns:create"},
    ]
    onboarding_complete = all(step["done"] for step in onboarding_steps)

    return render(
        request,
        "campaigns/dashboard.html",
        {
            "campaigns": recent_campaigns,
            "stats": stats,
            "onboarding_steps": onboarding_steps,
            "onboarding_complete": onboarding_complete,
        },
    )


@login_required
def create_campaign(request):
    if request.method == "POST":
        form = CampaignCreateForm(request.POST, user=request.user)
        if form.is_valid():
            campaign = form.save(commit=False)
            campaign.user = request.user
            campaign.save()
            build_recipients(campaign)
            messages.success(request, f"Campaign “{campaign.name}” created with {campaign.recipients.count()} recipients. Review it below before sending.")
            return redirect("campaigns:detail", pk=campaign.pk)
    else:
        form = CampaignCreateForm(user=request.user)

    data_files_columns = {f.pk: {"columns": f.columns, "email": f.detected_email_column} for f in request.user.data_files.all()}

    if not request.user.templates.exists() or not request.user.data_files.exists():
        messages.info(request, "You'll need at least one template and one uploaded data file before creating a campaign.")

    return render(
        request,
        "campaigns/create.html",
        {"form": form, "data_files_columns_json": json.dumps(data_files_columns)},
    )


@login_required
def campaign_detail(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk, user=request.user)
    recipients = campaign.recipients.all()[:200]
    counts = {
        "pending": campaign.recipients.filter(status="pending").count(),
        "sent": campaign.recipients.filter(status="sent").count(),
        "failed": campaign.recipients.filter(status="failed").count(),
        "skipped": campaign.recipients.filter(status="skipped").count(),
    }
    return render(request, "campaigns/detail.html", {"campaign": campaign, "recipients": recipients, "counts": counts})


@login_required
def send_campaign(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk, user=request.user)
    if request.method == "POST":
        if not campaign.sending_account:
            messages.error(request, "Select a sending account before sending.")
        else:
            pending_count = campaign.recipients.filter(status=CampaignRecipient.Status.PENDING).count()
            if pending_count > settings.SYNC_SEND_THRESHOLD:
                # Large campaigns are handed off to the background worker
                # (management command `send_pending_campaigns`, run on a
                # schedule) instead of sending inside the request, so the
                # request doesn't time out. See campaigns/sending_engine.py.
                if not campaign.started_at:
                    campaign.started_at = timezone.now()
                campaign.status = Campaign.Status.SENDING
                campaign.save(update_fields=["status", "started_at"])
                messages.success(
                    request,
                    f"Queued — {pending_count} emails will go out shortly via the background sender. "
                    "Refresh this page to see progress.",
                )
            else:
                send_campaign_now(campaign)
                messages.success(request, "Send finished (or paused at your account's daily limit — rerun tomorrow to continue).")
    return redirect("campaigns:detail", pk=campaign.pk)


def unsubscribe_confirm(request, token):
    """Public — no login required. A recipient lands here from the footer
    link in an email they were sent."""
    data = read_unsubscribe_token(token)
    if not data:
        return render(request, "campaigns/unsubscribe.html", {"invalid": True}, status=400)

    User = get_user_model()
    sender = get_object_or_404(User, pk=data["u"])
    email = data["e"]

    already_done = UnsubscribeEntry.objects.filter(user=sender, email=email).exists()

    if request.method == "POST":
        UnsubscribeEntry.objects.get_or_create(user=sender, email=email)
        return render(request, "campaigns/unsubscribe.html", {"email": email, "done": True})

    return render(request, "campaigns/unsubscribe.html", {"email": email, "already_done": already_done})
