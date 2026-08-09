# Massmailer

A multi-user web app for drafting customized ("mail merge") emails, with variable values pulled from an uploaded CSV/Excel file, sent from each user's own Gmail or Outlook account.

See `architecture-plan.md` (in the project's shared docs) for the full design rationale. This is a working v1 scaffold: signup/login, CSV/Excel upload + parsing, a template editor with live per-row merge preview, campaign creation, and a send pipeline — verified end to end in this session (see "What's been tested" below). Gmail/Outlook OAuth needs real credentials to actually send; everything else runs as-is.

## Quickstart (local dev, SQLite, no OAuth)

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env              # defaults are fine for local dev

python manage.py migrate
python manage.py createsuperuser  # optional, for /admin/
python manage.py runserver
```

Visit http://127.0.0.1:8000/ — sign up, upload a CSV/Excel file, draft a template, create a campaign. Sending will show a "needs to be reconnected" error until you configure real OAuth credentials (expected — see below).

## Connecting real Gmail/Outlook sending

1. Generate an encryption key for stored OAuth tokens:
   ```bash
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```
   Put it in `.env` as `FIELD_ENCRYPTION_KEY`.
2. Create OAuth credentials (see comments at the top of `sending/oauth.py` for exact scopes and console links) and put the client id/secret in `.env`.
3. Register the redirect URIs with each provider:
   - `{your domain}/sending-accounts/callback/google/`
   - `{your domain}/sending-accounts/callback/microsoft/`
4. Restart the app. The "Connect Gmail" / "Connect Outlook" buttons under Sending accounts will now work.

## Project layout

- `accounts/` — signup/login/logout (Django's built-in auth)
- `datafiles/` — CSV/Excel upload + parsing (`pandas`/`openpyxl`)
- `emailtemplates/` — template CRUD, `{{variable}}` merge engine, live preview endpoint
- `sending/` — OAuth connect flow + Gmail/Graph API send calls
- `campaigns/` — ties a template + data file + sending account together, builds the recipient list, runs the send

## What's been tested (this session)

Ran the app with `runserver` and drove it end to end via HTTP requests: signup, login, CSV upload (columns auto-detected, email column auto-guessed), template creation, the live merge-preview endpoint (`{{first_name}}` etc. substituted correctly per row), campaign creation (form correctly rejects a missing sending account), and the send pipeline (recipients built correctly from the CSV; a stubbed sending account correctly produced a graceful per-recipient "needs to be reconnected" failure rather than crashing, since no real OAuth token was present). `manage.py check` and `makemigrations`/`migrate` run clean.

Not yet tested: a real Gmail/Outlook send (needs OAuth credentials only you can create), Microsoft Graph path specifically (Gmail and Microsoft share the same code path, but only Gmail's request shape has been exercised), and behavior under concurrent/large campaigns.

## Known v1 limitations (see architecture-plan.md milestones for the roadmap)

- Sending is synchronous (runs inside the request) — fine for small campaigns/demos, but move to a background worker (a management command polling `status=SENDING` campaigns, run via cron on Render/Railway) before real volume.
- No email verification / CAPTCHA on signup yet — add before opening this up publicly, since it's a bulk-email tool.
- Unsubscribe entries have no UI yet (model + admin only) — add a public unsubscribe-link endpoint before real use.
- Uploaded files are re-parsed from disk on each preview/campaign-build — fine at the current file-size cap (10MB), but consider caching parsed rows for larger files.
