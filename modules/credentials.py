"""Encryption and retrieval helpers for user-owned credentials.

Secrets never cross this Module's public interface in logs or HTTP responses.
The primary key is ``CREDENTIAL_ENCRYPTION_KEY``.  The older Gmail key remains
as a decrypt-only compatibility key so existing Gmail integrations keep working
during the production migration.
"""

from __future__ import annotations

import json
import os
from typing import Any

from cryptography.fernet import Fernet, InvalidToken, MultiFernet


class CredentialError(ValueError):
    """Raised when encrypted credentials cannot be used safely."""


def _configured_fernet_keys() -> list[bytes]:
    """Return the active key followed by compatible legacy keys, without duplicates."""
    configured = [
        os.getenv("CREDENTIAL_ENCRYPTION_KEY"),
        os.getenv("GMAIL_TOKEN_ENCRYPTION_KEY"),
    ]
    keys: list[bytes] = []
    for value in configured:
        if not value:
            continue
        encoded = value.encode("utf-8")
        if encoded not in keys:
            keys.append(encoded)
    if not keys:
        raise CredentialError(
            "CREDENTIAL_ENCRYPTION_KEY must be configured before encrypted credentials can be used."
        )
    return keys


def credential_cipher() -> MultiFernet:
    """Build a key-rotation-aware cipher, validating all configured keys."""
    try:
        return MultiFernet([Fernet(key) for key in _configured_fernet_keys()])
    except Exception as exc:  # Fernet raises several implementation-specific errors.
        raise CredentialError("A configured credential encryption key is invalid.") from exc


def validate_credential_encryption_config() -> None:
    """Fail fast when a production process has no usable encryption key."""
    credential_cipher()


def encrypt_text(value: str) -> str:
    if not isinstance(value, str) or not value:
        raise CredentialError("A non-empty credential is required for encryption.")
    return credential_cipher().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_text(encrypted_value: str) -> str:
    if not isinstance(encrypted_value, str) or not encrypted_value:
        raise CredentialError("Stored credential is missing.")
    try:
        return credential_cipher().decrypt(encrypted_value.encode("utf-8")).decode("utf-8")
    except (InvalidToken, UnicodeDecodeError, ValueError) as exc:
        raise CredentialError("Stored credential cannot be decrypted. Reconnect or replace it.") from exc


def encrypt_json(value: dict[str, Any]) -> str:
    if not isinstance(value, dict):
        raise CredentialError("Credential data must be an object.")
    return encrypt_text(json.dumps(value, separators=(",", ":"), sort_keys=True))


def decrypt_json(encrypted_value: str) -> dict[str, Any]:
    try:
        value = json.loads(decrypt_text(encrypted_value))
    except json.JSONDecodeError as exc:
        raise CredentialError("Stored credential data is malformed. Reconnect or replace it.") from exc
    if not isinstance(value, dict):
        raise CredentialError("Stored credential data is malformed. Reconnect or replace it.")
    return value


def get_user_gemini_key(user_data: dict[str, Any] | None) -> str | None:
    """Read the encrypted key, with a temporary legacy fallback for migration."""
    if not isinstance(user_data, dict):
        return None
    encrypted_value = user_data.get("encrypted_gemini_api_key")
    if encrypted_value:
        return decrypt_text(encrypted_value)
    legacy_value = user_data.get("gemini_api_key")
    return legacy_value if isinstance(legacy_value, str) and legacy_value else None
