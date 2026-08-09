"""
Minimal OAuth 2.0 "authorization code" helpers for connecting a user's own
Gmail or Microsoft 365 mailbox so the app can send as them.

This is deliberately dependency-light (plain `requests` calls) rather than
pulling in `google-auth-oauthlib`/`msal`, so it's easy to read end to end.
Swap in the official SDKs later if you want built-in retry/refresh handling.

To make this live:
  1. Create OAuth credentials:
     - Google: https://console.cloud.google.com/apis/credentials
       Scopes needed: https://www.googleapis.com/auth/gmail.send,
                       https://www.googleapis.com/auth/userinfo.email
     - Microsoft: https://portal.azure.com (Azure AD App registrations)
       Scopes needed: Mail.Send, User.Read, offline_access
  2. Set the client id/secret + redirect URIs in your .env (see .env.example).
  3. Register the redirect URI in each provider's console as:
       {your domain}/sending-accounts/callback/google/
       {your domain}/sending-accounts/callback/microsoft/
"""
from dataclasses import dataclass
from urllib.parse import urlencode

import requests
from django.conf import settings


@dataclass
class ProviderConfig:
    key: str
    authorize_url: str
    token_url: str
    userinfo_url: str
    scopes: list
    client_id: str
    client_secret: str


def get_provider_config(provider: str) -> ProviderConfig:
    if provider == "google":
        return ProviderConfig(
            key="google",
            authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            userinfo_url="https://www.googleapis.com/oauth2/v2/userinfo",
            scopes=[
                "https://www.googleapis.com/auth/gmail.send",
                "https://www.googleapis.com/auth/userinfo.email",
                "openid",
            ],
            client_id=settings.GOOGLE_OAUTH_CLIENT_ID,
            client_secret=settings.GOOGLE_OAUTH_CLIENT_SECRET,
        )
    if provider == "microsoft":
        return ProviderConfig(
            key="microsoft",
            authorize_url="https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
            token_url="https://login.microsoftonline.com/common/oauth2/v2.0/token",
            userinfo_url="https://graph.microsoft.com/v1.0/me",
            scopes=["Mail.Send", "User.Read", "offline_access"],
            client_id=settings.MICROSOFT_OAUTH_CLIENT_ID,
            client_secret=settings.MICROSOFT_OAUTH_CLIENT_SECRET,
        )
    raise ValueError(f"Unknown provider: {provider}")


def is_configured(provider: str) -> bool:
    cfg = get_provider_config(provider)
    return bool(cfg.client_id and cfg.client_secret)


def build_authorize_url(provider: str, redirect_uri: str, state: str) -> str:
    cfg = get_provider_config(provider)
    params = {
        "client_id": cfg.client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(cfg.scopes),
        "access_type": "offline",  # Google: request a refresh_token
        "prompt": "consent",
        "state": state,
    }
    return f"{cfg.authorize_url}?{urlencode(params)}"


def exchange_code_for_tokens(provider: str, code: str, redirect_uri: str) -> dict:
    cfg = get_provider_config(provider)
    resp = requests.post(
        cfg.token_url,
        data={
            "client_id": cfg.client_id,
            "client_secret": cfg.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()  # contains access_token, refresh_token, expires_in, ...


def refresh_access_token(provider: str, refresh_token: str) -> dict:
    """Exchange a stored refresh_token for a fresh access_token."""
    cfg = get_provider_config(provider)
    resp = requests.post(
        cfg.token_url,
        data={
            "client_id": cfg.client_id,
            "client_secret": cfg.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()  # contains a new access_token (+ expires_in; refresh_token usually unchanged)


def fetch_email_address(provider: str, access_token: str) -> str:
    cfg = get_provider_config(provider)
    resp = requests.get(cfg.userinfo_url, headers={"Authorization": f"Bearer {access_token}"}, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    return data.get("email") or data.get("mail") or data.get("userPrincipalName", "")
