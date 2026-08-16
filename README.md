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

## Deploying to Render

This repo includes `render.yaml` (a Render "Blueprint") and `build.sh`, so Render can stand up the web service and a managed Postgres database from the repo with no manual service configuration.

1. Push this repo to GitHub (see below if you haven't yet).
2. In the Render dashboard: **New +** → **Blueprint**, then connect and select this repo. Render will detect `render.yaml` automatically.
3. Render will provision a free Postgres database (`massmailer-db`) and a free web service (`massmailer`), wiring `DATABASE_URL` and a generated `DJANGO_SECRET_KEY` automatically.
4. Before the first deploy finishes successfully, fill in these env vars on the web service (Render dashboard → the service → Environment) — they're intentionally left blank in the blueprint since they're secrets:
   - `FIELD_ENCRYPTION_KEY` — generate with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`. Required before any Gmail/Outlook account can be connected.
   - `GOOGLE_OAUTH_CLIENT_ID` / `GOOGLE_OAUTH_CLIENT_SECRET` and/or `MICROSOFT_OAUTH_CLIENT_ID` / `MICROSOFT_OAUTH_CLIENT_SECRET` — see `sending/oauth.py` for where to get these. You can deploy without them; the "Connect Gmail/Outlook" buttons will just show a "not configured" message until they're set.
5. Once deployed, register the OAuth redirect URIs with Google/Microsoft using your live Render URL:
   - `https://{your-render-subdomain}.onrender.com/sending-accounts/callback/google/`
   - `https://{your-render-subdomain}.onrender.com/sending-accounts/callback/microsoft/`
6. The free Postgres plan expires after 30 days and the free web service spins down after inactivity (cold start on the next request) — fine for testing, upgrade the plans in Render when you're ready for real users.

`ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` pick up Render's own hostname automatically (`RENDER_EXTERNAL_HOSTNAME`, set by Render on every service) — no extra config needed there.

## Processing large campaigns in the background

Campaigns with more than `SYNC_SEND_THRESHOLD` (default 25) pending recipients aren't sent inside the web request — that would risk a timeout. Clicking "Send now" on one of these just queues it (status becomes `SENDING`); a separate command finishes the job:

```bash
python manage.py send_pending_campaigns
```

Small campaigns still send instantly on click, no queue involved.

To automate this instead of running it by hand:
- **Render Cron Job** (needs a paid plan — the free tier doesn't support background workers or cron): add a service to `render.yaml` with `type: cron`, the same `buildCommand` as the web service, and `startCommand: "python manage.py send_pending_campaigns"`, on whatever schedule fits your volume (every few minutes is reasonable).
- Any other scheduler (GitHub Actions, a VM's crontab, etc.) that can reach a `manage.py` shell against the same database.

## Getting this onto GitHub

If you haven't pushed yet:
```bash
git remote add origin https://github.com/<you>/<repo>.git   # already set if you're using the copy this session prepared
git push -u origin main
```

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

- No email verification on signup yet (honeypot + IP rate-limiting are in place — see "Compliance & abuse prevention" below — but there's no "confirm your address" step). Add before opening this up broadly.
- The per-run daily-send-limit check in `campaigns/sending_engine.py` counts sends *within that run*, not across multiple runs/resumes in the same day — if a campaign is resumed several times in one day it can exceed the configured daily cap. Fine at v1 scale; track cumulative sends per account per day before relying on this for a provider-enforced limit.
- Uploaded files are re-parsed from disk on each preview/campaign-build — fine at the current file-size cap (10MB), but consider caching parsed rows for larger files.
- The background send worker (`send_pending_campaigns`) isn't safe to run as multiple concurrent workers against the same campaign (no row locking) — run it as a single scheduled job.
- Rate limiting uses Django's default in-process cache, which resets on every deploy/restart and doesn't share state across multiple web dynos — fine for Render's free single-instance plan; move to a shared cache (Redis) before scaling horizontally.

## Compliance & abuse prevention (milestone 6)

- **Unsubscribe**: every sent email gets an automatic footer with a working, no-login-required unsubscribe link (`campaigns/tokens.py` + `campaigns/views.py::unsubscribe_confirm`). Recipients who click it are excluded from that sender's future campaigns at build time (`campaigns/sending_engine.py::build_recipients`).
- **Signup abuse safeguards**: a honeypot field on the signup form (`accounts/forms.py`), plus IP-based rate limiting on signup and login (`core/ratelimit.py`, tunable via `SIGNUP_RATE_LIMIT_*`/`LOGIN_RATE_LIMIT_*` env vars). No CAPTCHA/external service required.
- **High-volume account flagging**: `/admin/` surfaces each campaign's sending user's total sends in the last 24h and flags accounts over `SUSPICIOUS_DAILY_SEND_THRESHOLD` (default 2000) for manual review — it doesn't block sending, per the platform's "make compliance easy, but sends go out as the user" policy in `architecture-plan.md`.
