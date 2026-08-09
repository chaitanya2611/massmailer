import secrets
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from . import oauth
from .models import SendingAccount


@login_required
def list_accounts(request):
    accounts = request.user.sending_accounts.all()
    return render(
        request,
        "sending/list.html",
        {
            "accounts": accounts,
            "google_configured": oauth.is_configured("google"),
            "microsoft_configured": oauth.is_configured("microsoft"),
        },
    )


@login_required
def connect_start(request, provider):
    if provider not in ("google", "microsoft"):
        messages.error(request, "Unknown provider.")
        return redirect("sending:list")

    if not oauth.is_configured(provider):
        messages.error(
            request,
            f"{provider.title()} OAuth isn't configured yet on this server — "
            f"an admin needs to set {provider.upper()}_OAUTH_CLIENT_ID/SECRET in .env. "
            "See sending/oauth.py for setup instructions.",
        )
        return redirect("sending:list")

    state = secrets.token_urlsafe(24)
    request.session[f"oauth_state_{provider}"] = state
    redirect_uri = request.build_absolute_uri(reverse("sending:callback", args=[provider]))
    auth_url = oauth.build_authorize_url(provider, redirect_uri, state)
    return redirect(auth_url)


@login_required
def oauth_callback(request, provider):
    if provider not in ("google", "microsoft"):
        messages.error(request, "Unknown provider.")
        return redirect("sending:list")

    expected_state = request.session.pop(f"oauth_state_{provider}", None)
    returned_state = request.GET.get("state")
    code = request.GET.get("code")

    if not code or not expected_state or expected_state != returned_state:
        messages.error(request, "OAuth connection failed or was cancelled (state mismatch).")
        return redirect("sending:list")

    redirect_uri = request.build_absolute_uri(reverse("sending:callback", args=[provider]))
    try:
        tokens = oauth.exchange_code_for_tokens(provider, code, redirect_uri)
        email = oauth.fetch_email_address(provider, tokens["access_token"])
    except Exception as exc:
        messages.error(request, f"Couldn't finish connecting your {provider.title()} account: {exc}")
        return redirect("sending:list")

    expires_in = tokens.get("expires_in", 3600)
    account, _created = SendingAccount.objects.update_or_create(
        user=request.user,
        provider=provider,
        sender_email=email,
        defaults={
            "access_token": tokens.get("access_token", ""),
            "refresh_token": tokens.get("refresh_token", ""),
            "token_expires_at": timezone.now() + timedelta(seconds=expires_in),
            "scopes": tokens.get("scope", ""),
            "status": SendingAccount.Status.ACTIVE,
        },
    )
    messages.success(request, f"Connected {account.sender_email}. You can now send campaigns from this address.")
    return redirect("sending:list")


@login_required
def disconnect(request, pk):
    account = get_object_or_404(SendingAccount, pk=pk, user=request.user)
    if request.method == "POST":
        email = account.sender_email
        account.delete()
        messages.success(request, f"Disconnected {email}.")
    return redirect("sending:list")
