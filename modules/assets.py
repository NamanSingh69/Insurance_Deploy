# modules/assets.py
import os
import uuid
from datetime import datetime, timedelta
from db import db

def create_asset(user_id, storage_kind, storage_locator, filename='', mime_type='', expires_at=None, report_id=None):
    """Create an application-owned reference to a private stored file."""
    return db.create_asset(
        user_id, storage_kind, storage_locator, filename=filename,
        mime_type=mime_type, expires_at=expires_at, report_id=report_id
    )

def get_asset_for_user(asset_id, user_id):
    """Return an asset only when the requesting user owns it and it has not expired."""
    return db.get_asset_for_user(asset_id, user_id)

def get_owned_asset_content(asset_id, user_id):
    """Retrieve content of an owned asset from Drive or local workspace storage."""
    asset = db.get_asset_for_user(asset_id, user_id)
    if not isinstance(asset, dict):
        return None, None

    # Base folder path is project root (parent directory of modules/)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    if asset.get('storage_kind') == 'drive':
        return db.get_file_content(asset.get('storage_locator')), asset

    if asset.get('storage_kind') in {'local', 'legacy_local'}:
        filename = os.path.basename(asset.get('storage_locator', ''))
        storage_dir = 'assets' if asset.get('storage_kind') == 'local' else ''
        local_path = os.path.join(project_root, 'uploads', storage_dir, filename)
        try:
            with open(local_path, 'rb') as f:
                return f.read(), asset
        except OSError:
            return None, asset

    if asset.get('storage_kind') == 'job_local':
        filename = os.path.basename(asset.get('storage_locator', ''))
        local_path = os.path.join(project_root, 'uploads', 'job_inputs', filename)
        try:
            with open(local_path, 'rb') as f:
                return f.read(), asset
        except OSError:
            return None, asset

    return None, asset

def delete_expired_assets():
    """Retrieve expired storage records for clean up and delete them."""
    return db.delete_expired_assets()

def migrate_legacy_photo_references():
    """Migrate old image references to assets."""
    return db.migrate_legacy_photo_references()

def upload_image_to_drive(file_content, filename, mime_type='image/jpeg'):
    """Uploads file to private Google Drive storage."""
    return db.upload_image_to_drive(file_content, filename, mime_type=mime_type)

def upload_report_pdf(pdf_bytes, filename, vehicle_no):
    """Uploads completed PDF to private Google Drive storage."""
    return db.upload_report_pdf(pdf_bytes, filename, vehicle_no)
