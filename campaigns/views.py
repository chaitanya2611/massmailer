import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CampaignCreateForm
from .models import Campaign
from .sending_engine import build_recipients, send_campaign_now


@login_required
def dashboard(request):
    campaigns = request.user.campaigns.all()
    return render(request, "campaigns/dashboard.html", {"campaigns": campaigns})


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
            send_campaign_now(campaign)
            messages.success(request, "Send finished (or paused at your account's daily limit — rerun tomorrow to continue).")
    return redirect("campaigns:detail", pk=campaign.pk)
