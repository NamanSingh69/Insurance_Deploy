"""Server-side Google Drive authorization and report delivery.

The browser only learns whether Drive is connected and receives the resulting
report link.  OAuth access and refresh tokens remain encrypted at rest and are
never copied into Flask's client-side session cookie.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

import requests

from db import db
from modules.credentials import CredentialError, decrypt_json, encrypt_json


GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_REVOKE_URL = "https://oauth2.googleapis.com/revoke"
GOOGLE_DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"
GOOGLE_DRIVE_UPLOAD_URL = "https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable"
GOOGLE_FOLDER_MIME = "application/vnd.google-apps.folder"


class DriveAuthorizationError(ValueError):
    """Raised when a user needs to connect or reconnect Drive."""


def _oauth_client() -> tuple[str, str]:
    client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise DriveAuthorizationError("Google Drive authorization is not configured.")
    return client_id, client_secret


def _expiry_from_tokens(tokens: dict[str, Any]) -> datetime | None:
    value = tokens.get("expires_at")
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def _normalized_tokens(tokens: dict[str, Any], previous: dict[str, Any] | None = None) -> dict[str, Any]:
    if not isinstance(tokens, dict):
        raise DriveAuthorizationError("Google Drive returned malformed authorization data.")
    output = dict(previous or {})
    output.update({key: value for key, value in tokens.items() if value is not None})
    if not output.get("refresh_token"):
        raise DriveAuthorizationError("Google Drive did not return a refresh token. Reconnect and grant consent.")
    if not output.get("access_token"):
        raise DriveAuthorizationError("Google Drive did not return an access token. Reconnect and try again.")
    expires_in = tokens.get("expires_in")
    if expires_in is not None:
        try:
            output["expires_at"] = (datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))).isoformat()
        except (TypeError, ValueError):
            pass
    return output


def _database():
    """Use the injected database adapter in request tests; workers use the real store."""
    try:
        from flask import current_app
        return current_app.config.get('DB_ADAPTER', db)
    except RuntimeError:
        return db


def save_drive_authorization(user_id: str | int, tokens: dict[str, Any], account_email: str | None = None) -> bool:
    """Encrypt and persist a completed OAuth exchange for one user."""
    normalized = _normalized_tokens(tokens)
    return _database().save_drive_integration(user_id, encrypt_json(normalized), account_email)


def _load_drive_tokens(user_id: str | int) -> tuple[dict[str, Any], dict[str, Any]]:
    record = _database().get_drive_integration(user_id)
    if not record:
        raise DriveAuthorizationError("Google Drive is not connected.")
    try:
        tokens = decrypt_json(record.get("encrypted_token", ""))
    except CredentialError as exc:
        raise DriveAuthorizationError("Saved Google Drive authorization is invalid. Please reconnect.") from exc
    return tokens, record


def _refresh_drive_tokens(user_id: str | int, tokens: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    client_id, client_secret = _oauth_client()
    try:
        response = requests.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": tokens.get("refresh_token"),
                "grant_type": "refresh_token",
            },
            timeout=15,
        )
    except requests.RequestException as exc:
        raise DriveAuthorizationError("Could not refresh Google Drive authorization. Please try again.") from exc
    if response.status_code != 200:
        raise DriveAuthorizationError("Google Drive authorization expired. Please reconnect.")
    try:
        refreshed = _normalized_tokens(response.json(), previous=tokens)
    except (ValueError, DriveAuthorizationError) as exc:
        raise DriveAuthorizationError("Google Drive authorization expired. Please reconnect.") from exc
    if not _database().save_drive_integration(user_id, encrypt_json(refreshed), record.get("account_email")):
        raise DriveAuthorizationError("Could not save refreshed Google Drive authorization.")
    return refreshed


def get_drive_access_token(user_id: str | int) -> str:
    """Return a short-lived token only within server-side execution."""
    tokens, record = _load_drive_tokens(user_id)
    expiry = _expiry_from_tokens(tokens)
    if not tokens.get("access_token") or not expiry or expiry <= datetime.now(timezone.utc) + timedelta(seconds=60):
        tokens = _refresh_drive_tokens(user_id, tokens, record)
    token = tokens.get("access_token")
    if not isinstance(token, str) or not token:
        raise DriveAuthorizationError("Google Drive authorization is invalid. Please reconnect.")
    return token


def is_drive_connected(user_id: str | int) -> bool:
    return bool(_database().get_drive_integration(user_id))


def disconnect_drive(user_id: str | int) -> bool:
    """Best-effort remote revocation followed by local encrypted-record removal."""
    try:
        tokens, _ = _load_drive_tokens(user_id)
        token = tokens.get("refresh_token") or tokens.get("access_token")
        if token:
            try:
                requests.post(GOOGLE_REVOKE_URL, params={"token": token}, timeout=15)
            except requests.RequestException:
                # Local deletion is still important; users can revoke remotely
                # from Google if their network is unavailable right now.
                pass
    except DriveAuthorizationError:
        pass
    return _database().delete_drive_integration(user_id)


def _headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def _query_literal(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _get_or_create_folder(access_token: str, name: str, parent_id: str | None = None) -> str:
    query = f"name = '{_query_literal(name)}' and mimeType = '{GOOGLE_FOLDER_MIME}' and trashed = false"
    if parent_id:
        query += f" and '{parent_id}' in parents"
    response = requests.get(
        GOOGLE_DRIVE_FILES_URL,
        headers=_headers(access_token),
        params={"q": query, "pageSize": 1, "fields": "files(id)"},
        timeout=20,
    )
    if response.status_code == 200:
        files = response.json().get("files", [])
        if files and files[0].get("id"):
            return files[0]["id"]
    metadata: dict[str, Any] = {"name": name, "mimeType": GOOGLE_FOLDER_MIME}
    if parent_id:
        metadata["parents"] = [parent_id]
    response = requests.post(
        GOOGLE_DRIVE_FILES_URL,
        headers={**_headers(access_token), "Content-Type": "application/json"},
        json=metadata,
        timeout=20,
    )
    if response.status_code not in (200, 201):
        raise DriveAuthorizationError("Could not create the Google Drive destination folder.")
    folder_id = response.json().get("id")
    if not folder_id:
        raise DriveAuthorizationError("Google Drive did not return a destination folder.")
    return folder_id


def upload_report_to_personal_drive(user_id: str | int, pdf_bytes: bytes, filename: str, folder_name: str) -> str:
    """Put a generated report into the connected user's private Drive folder."""
    access_token = get_drive_access_token(user_id)
    root_folder = _get_or_create_folder(access_token, "Survey Reports")
    destination_folder = _get_or_create_folder(access_token, folder_name or "Unknown Vehicle", root_folder)
    start = requests.post(
        GOOGLE_DRIVE_UPLOAD_URL,
        headers={
            **_headers(access_token),
            "Content-Type": "application/json",
            "X-Upload-Content-Type": "application/pdf",
            "X-Upload-Content-Length": str(len(pdf_bytes)),
        },
        json={"name": filename, "mimeType": "application/pdf", "parents": [destination_folder]},
        timeout=30,
    )
    upload_url = start.headers.get("Location") if start.status_code in (200, 201) else None
    if not upload_url:
        raise DriveAuthorizationError("Could not start the Google Drive report upload.")
    complete = requests.put(
        upload_url,
        headers={**_headers(access_token), "Content-Type": "application/pdf"},
        data=pdf_bytes,
        timeout=180,
    )
    if complete.status_code not in (200, 201):
        raise DriveAuthorizationError("Could not upload the report to Google Drive.")
    file_id = complete.json().get("id")
    if not file_id:
        raise DriveAuthorizationError("Google Drive did not return the uploaded report.")
    metadata = requests.get(
        f"{GOOGLE_DRIVE_FILES_URL}/{file_id}",
        headers=_headers(access_token),
        params={"fields": "webViewLink"},
        timeout=20,
    )
    if metadata.status_code == 200 and metadata.json().get("webViewLink"):
        return metadata.json()["webViewLink"]
    return f"https://drive.google.com/open?id={file_id}"
