import os
from cryptography.fernet import Fernet, InvalidToken
from django.core.management.base import CommandError

KEY_ENV_NAME = "BACKUP_ENCRYPTION_KEY"


def get_fernet():
    raw_key = (os.getenv(KEY_ENV_NAME) or "").strip()
    if not raw_key:
        raise CommandError(f"{KEY_ENV_NAME} is not set. Generate one with Fernet.generate_key().")
    try:
        return Fernet(raw_key.encode("utf-8"))
    except (ValueError, TypeError) as exc:
        raise CommandError(f"{KEY_ENV_NAME} is not a valid Fernet key: {exc}") from exc


def encrypt_bytes(data):
    return get_fernet().encrypt(data)


def decrypt_bytes(token):
    try:
        return get_fernet().decrypt(token)
    except InvalidToken as exc:
        raise CommandError("Backup decryption failed: wrong key or corrupted file.") from exc
