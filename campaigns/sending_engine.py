"""
Builds a campaign's recipient list from its data file, and sends it.

v1 note: `send_campaign_now` runs synchronously inside the request/response
cycle, which is fine for small campaigns/demos but will time out on large
ones. The next step (see architecture-plan.md milestone 5) is to move this
into a background worker (a management command polling for
status=SENDING campaigns, run via cron or a worker dyno on Render/Railway)
instead of calling it directly from the view.
"""
from django.utils import timezone

from datafiles.parsing import parse_tabular_file
from emailtemplates.merge import missing_variables, render_merge

from .models import Campaign, CampaignRecipient, UnsubscribeEntry


def build_recipients(campaign: Campaign):
    """Parse the campaign's data file and create one CampaignRecipient per row."""
    data_file = campaign.data_file
    data_file.file.open("rb")
    try:
        _, records, _ = parse_tabular_file(data_file.file)
    finally:
        data_file.file.close()

    unsubscribed = set(
        UnsubscribeEntry.objects.filter(user=campaign.user).values_list("email", flat=True)
    )
    unsubscribed = {e.strip().lower() for e in unsubscribed}

    recipients = []
    for row in records:
        email = str(row.get(campaign.email_column, "")).strip()
        status = CampaignRecipient.Status.PENDING
        error = ""
        if not email:
            status = CampaignRecipient.Status.SKIPPED
            error = f"No value in '{campaign.email_column}' column."
        elif email.lower() in unsubscribed:
            status = CampaignRecipient.Status.SKIPPED
            error = "Recipient is on the unsubscribe list."
        recipients.append(
            CampaignRecipient(campaign=campaign, row_data=row, resolved_email=email, status=status, error_message=error)
        )

    CampaignRecipient.objects.bulk_create(recipients)


def send_campaign_now(campaign: Campaign):
    """Send all still-pending recipients for this campaign, synchronously."""
    account = campaign.sending_account
    if not account:
        campaign.status = Campaign.Status.FAILED
        campaign.save(update_fields=["status"])
        return

    from sending.mailer import SendError, send_email

    campaign.status = Campaign.Status.SENDING
    campaign.started_at = timezone.now()
    campaign.save(update_fields=["status", "started_at"])

    sent_this_run = 0
    pending = campaign.recipients.filter(status=CampaignRecipient.Status.PENDING)

    for recipient in pending:
        if sent_this_run >= account.daily_send_limit:
            recipient.status = CampaignRecipient.Status.SKIPPED
            recipient.error_message = "Skipped: would exceed the sending account's daily limit. Resume tomorrow."
            recipient.save(update_fields=["status", "error_message"])
            continue

        subject = render_merge(campaign.template.subject, recipient.row_data)
        body = render_merge(campaign.template.body, recipient.row_data)
        missing = missing_variables(campaign.template.subject, recipient.row_data) + missing_variables(
            campaign.template.body, recipient.row_data
        )
        if missing:
            recipient.status = CampaignRecipient.Status.SKIPPED
            recipient.error_message = f"Missing values for: {', '.join(missing)}"
            recipient.save(update_fields=["status", "error_message"])
            continue

        try:
            send_email(account, recipient.resolved_email, subject, body, is_html=campaign.template.is_html)
        except SendError as exc:
            recipient.status = CampaignRecipient.Status.FAILED
            recipient.error_message = str(exc)
            recipient.save(update_fields=["status", "error_message"])
        else:
            recipient.status = CampaignRecipient.Status.SENT
            recipient.sent_at = timezone.now()
            recipient.save(update_fields=["status", "sent_at"])
            sent_this_run += 1

    still_pending = campaign.recipients.filter(status=CampaignRecipient.Status.PENDING).exists()
    campaign.status = Campaign.Status.SENDING if still_pending else Campaign.Status.COMPLETED
    if not still_pending:
        campaign.completed_at = timezone.now()
    campaign.save(update_fields=["status", "completed_at"])
