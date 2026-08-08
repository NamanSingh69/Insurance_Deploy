"""Private-file ownership and storage helpers.

Every browser-visible file is represented by an ``assets`` row and is served
through an authenticated route.  Files are never placed in ``static/`` or
addressed by an upstream provider identifier supplied by the browser.
"""

from __future__ import annotations

import hashlib
import io
import os
import uuid
import warnings
from datetime import datetime, timedelta
from pathlib import Path
from typing import BinaryIO

from PIL import Image, UnidentifiedImageError

from db import db


MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_IMAGE_PIXELS = 20_000_000
MAX_PDF_BYTES = 100 * 1024 * 1024
_IMAGE_FORMATS = {
    "JPEG": ("image/jpeg", ".jpg"),
    "PNG": ("image/png", ".png"),
    "WEBP": ("image/webp", ".webp"),
}


def _database():
    """Use the injected database in tests while workers use the production store."""
    try:
        from flask import current_app
        return current_app.config.get('DB_ADAPTER', db)
    except RuntimeError:
        return db


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def private_storage_root() -> Path:
    """Return a non-public, process-owned directory for private bytes."""
    configured = os.getenv("PRIVATE_STORAGE_DIR")
    root = Path(configured) if configured else _project_root() / "instance" / "private_assets"
    root.mkdir(parents=True, exist_ok=True)
    try:
        root.chmod(0o700)
    except OSError:
        # Windows does not support POSIX modes; the deployment service applies
        # ownership and restrictive ACLs on Linux.
        pass
    return root


def _private_path(locator: str) -> Path:
    filename = os.path.basename(locator or "")
    if not filename or filename != locator:
        raise ValueError("Invalid private asset locator.")
    return private_storage_root() / filename


def _legacy_path(storage_kind: str, locator: str) -> Path:
    """Resolve only previous private locations while legacy rows are migrated."""
    filename = os.path.basename(locator or "")
    if not filename:
        raise ValueError("Invalid legacy asset locator.")
    root = _project_root() / "uploads"
    if storage_kind == "local":
        root = root / "assets"
    elif storage_kind == "job_local":
        root = root / "job_inputs"
    return root / filename


def _write_private_bytes(content: bytes, suffix: str) -> str:
    locator = f"{uuid.uuid4().hex}{suffix}"
    target = _private_path(locator)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    try:
        descriptor = os.open(target, flags, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        try:
            target.unlink(missing_ok=True)
        except OSError:
            pass
        raise
    return locator


def _extension_for_mime(mime_type: str, filename: str = "") -> str:
    ext = Path(filename).suffix.lower()
    expected = {
        "application/pdf": ".pdf",
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
    }.get(mime_type)
    return expected or (ext if 0 < len(ext) <= 10 else ".bin")


def validate_pdf_bytes(content: bytes) -> str:
    if not content:
        raise ValueError("The PDF is empty.")
    if len(content) > MAX_PDF_BYTES:
        raise ValueError("PDF files must be 100 MB or smaller.")
    if not content.startswith(b"%PDF-"):
        raise ValueError("The uploaded file is not a valid PDF.")
    return "application/pdf"


def validate_image_bytes(content: bytes) -> tuple[str, str]:
    if not content:
        raise ValueError("The image is empty.")
    if len(content) > MAX_IMAGE_BYTES:
        raise ValueError("Image files must be 10 MB or smaller.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(content)) as image:
                image.verify()
            with Image.open(io.BytesIO(content)) as image:
                image.load()
                if image.width * image.height > MAX_IMAGE_PIXELS:
                    raise ValueError("Image dimensions exceed the 20 megapixel limit.")
                format_name = image.format
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, ValueError) as exc:
        if isinstance(exc, ValueError) and "20 megapixel" in str(exc):
            raise
        raise ValueError("The uploaded file is not a supported image.") from exc
    if format_name not in _IMAGE_FORMATS:
        raise ValueError("Only JPEG, PNG, and WebP images are allowed.")
    return _IMAGE_FORMATS[format_name]


def create_asset(user_id, storage_kind, storage_locator, filename='', mime_type='', expires_at=None,
                 report_id=None, purpose='generic', size_bytes=None, checksum_sha256=None):
    return _database().create_asset(
        user_id, storage_kind, storage_locator, filename=filename, mime_type=mime_type,
        expires_at=expires_at, report_id=report_id, purpose=purpose,
        size_bytes=size_bytes, checksum_sha256=checksum_sha256,
    )


def store_private_bytes(user_id, content: bytes, filename: str, mime_type: str, purpose: str,
                        expires_at: datetime | None = None, report_id: str | None = None):
    """Write validated bytes privately, then create the durable ownership row."""
    if isinstance(content, str):
        content = content.encode('latin1')
    elif not isinstance(content, (bytes, bytearray)):
        raise ValueError("Uploaded content must be binary data.")
    content = bytes(content)
    locator = _write_private_bytes(content, _extension_for_mime(mime_type, filename))
    asset = create_asset(
        user_id=user_id,
        storage_kind="private_local",
        storage_locator=locator,
        filename=os.path.basename(filename)[:255],
        mime_type=mime_type,
        expires_at=expires_at,
        report_id=report_id,
        purpose=purpose,
        size_bytes=len(content),
        checksum_sha256=hashlib.sha256(content).hexdigest(),
    )
    if not asset:
        try:
            _private_path(locator).unlink(missing_ok=True)
        except OSError:
            pass
        raise RuntimeError("Could not create the uploaded-file record.")
    return asset


def store_uploaded_pdf(user_id, file_storage, purpose="pdf_input", ttl_hours=24):
    filename = os.path.basename(getattr(file_storage, "filename", "") or "document.pdf")
    content = file_storage.read()
    mime_type = validate_pdf_bytes(content)
    return store_private_bytes(
        user_id, content, filename, mime_type, purpose,
        expires_at=datetime.utcnow() + timedelta(hours=ttl_hours),
    )


def store_uploaded_image(user_id, file_storage, purpose="photo", expires_at=None):
    filename = os.path.basename(getattr(file_storage, "filename", "") or "image")
    content = file_storage.read()
    mime_type, _ = validate_image_bytes(content)
    return store_private_bytes(user_id, content, filename, mime_type, purpose, expires_at=expires_at)


def get_asset_for_user(asset_id, user_id):
    return _database().get_asset_for_user(asset_id, user_id)


def get_asset_for_access(asset_id, user_id, workspace_admin_id=None):
    return _database().get_asset_for_access(asset_id, user_id, workspace_admin_id)


def read_asset_content(asset):
    """Read only a server-recorded location; callers must authorize first."""
    if not isinstance(asset, dict):
        return None
    storage_kind = asset.get("storage_kind")
    locator = asset.get("storage_locator", "")
    try:
        if storage_kind == "drive":
            return _database().get_file_content(locator)
        if storage_kind == "private_local":
            return _private_path(locator).read_bytes()
        if storage_kind in {"local", "legacy_local", "job_local"}:
            return _legacy_path(storage_kind, locator).read_bytes()
    except OSError:
        return None
    return None


def get_owned_asset_content(asset_id, user_id):
    asset = get_asset_for_user(asset_id, user_id)
    return read_asset_content(asset), asset


def get_accessible_asset_content(asset_id, user_id, workspace_admin_id=None):
    asset = get_asset_for_access(asset_id, user_id, workspace_admin_id)
    return read_asset_content(asset), asset


def delete_asset_storage(asset):
    """Remove local bytes for an already-deleted asset row when possible."""
    if not isinstance(asset, dict):
        return
    try:
        storage_kind = asset.get("storage_kind")
        if storage_kind == "private_local":
            _private_path(asset.get("storage_locator", "")).unlink(missing_ok=True)
        elif storage_kind in {"local", "legacy_local", "job_local"}:
            _legacy_path(storage_kind, asset.get("storage_locator", "")).unlink(missing_ok=True)
    except (OSError, ValueError):
        return


def delete_expired_assets():
    return _database().delete_expired_assets()


def migrate_legacy_photo_references():
    return _database().migrate_legacy_photo_references()


def upload_image_to_drive(file_content, filename, mime_type='image/jpeg'):
    """Compatibility helper for legacy callers; new uploads use private assets."""
    return _database().upload_image_to_drive(file_content, filename, mime_type=mime_type)


def upload_report_pdf(pdf_bytes, filename, vehicle_no):
    return _database().upload_report_pdf(pdf_bytes, filename, vehicle_no)
