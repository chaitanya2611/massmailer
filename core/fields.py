"""Small shared utilities used across apps."""
from django.conf import settings
from django.db import models


def _get_fernet():
    from cryptography.fernet import Fernet

    key = settings.FIELD_ENCRYPTION_KEY
    if not key:
        raise RuntimeError(
            "FIELD_ENCRYPTION_KEY is not set. Generate one with:\n"
            "  python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"\n"
            "and put it in your .env file before storing OAuth tokens."
        )
    return Fernet(key.encode() if isinstance(key, str) else key)


class EncryptedTextField(models.TextField):
    """
    A TextField that transparently encrypts/decrypts its value at rest using
    Fernet (symmetric encryption). Used for OAuth refresh/access tokens so
    they aren't stored as plaintext in the database.

    Note: this encrypts at the application layer, which is a reasonable
    default for a small-to-mid deployment. For stricter requirements, move
    to a KMS-backed secret store instead.
    """

    description = "Text encrypted at rest with Fernet"

    def get_prep_value(self, value):
        if value is None or value == "":
            return value
        f = _get_fernet()
        return f.encrypt(str(value).encode()).decode()

    def from_db_value(self, value, expression, connection):
        if value is None or value == "":
            return value
        f = _get_fernet()
        try:
            return f.decrypt(value.encode()).decode()
        except Exception:
            # Value predates encryption or key rotated — surface as empty
            # rather than crashing page loads; callers should treat this as
            # "needs reconnect".
            return ""
