"""
Signed, stateless tokens for the public unsubscribe link.

Emails go out through the *user's own* mailbox rather than a shared
transactional-email provider, so there's no third-party suppression list —
this app has to run its own, and the link a recipient clicks has to work
without them being logged in. A `django.core.signing` token keyed on
(sending user id, recipient email) lets us verify the click is genuine
without a database lookup, and without ever putting a guessable id in the
URL that would let someone unsubscribe an address they don't own.
"""
from django.core import signing

SALT = "campaigns.unsubscribe"

# Tokens don't need to be single-use — clicking twice is harmless (the
# second click just finds the entry already there) — so no expiry is
# enforced. max_age is left unset on verification for that reason.


def make_unsubscribe_token(user_id: int, email: str) -> str:
    return signing.dumps({"u": user_id, "e": email.strip().lower()}, salt=SALT)


def read_unsubscribe_token(token: str):
    """Returns {"u": user_id, "e": email} or None if the token is invalid/tampered."""
    try:
        data = signing.loads(token, salt=SALT)
    except signing.BadSignature:
        return None
    if not isinstance(data, dict) or "u" not in data or "e" not in data:
        return None
    return data
