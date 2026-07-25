# modules/jobs.py
import os
import json
import uuid
import time
from datetime import datetime, timedelta
from db import db

def create_job(user_id, kind, input_data=None):
    """Create a new background job in PostgreSQL."""
    return db.create_job(user_id, kind, input_data)

def get_job_for_user(job_id, user_id):
    """Retrieve job details and enforce owner verification."""
    job = db.get_job_for_user(job_id, user_id)
    if isinstance(job, dict):
        result = job.get("result_json")
        if isinstance(result, str):
            try:
                result = json.loads(result)
            except json.JSONDecodeError:
                result = None
        
        # Enforce UI status mapping (running/queued map to 'processing' for browser polling)
        status = job.get("status")
        if status in ("queued", "running"):
            ui_status = "processing"
        else:
            ui_status = status

        return {
            "status": ui_status,
            "result": result,
            "error": job.get("error_message"),
            "kind": job.get("kind"),
            "user_id": job.get("user_id")
        }
    return None

def claim_next_job(worker_id):
    """Atomically claim one queued job from the queue."""
    return db.claim_next_job(worker_id)

def complete_job(job_id, result_data):
    """Complete a job with result payload."""
    return db.complete_job(job_id, result_data)

def fail_job(job_id, error_message):
    """Fail a job with an error message."""
    return db.fail_job(job_id, error_message)

def requeue_stale_jobs(stale_after_minutes=15):
    """Recover jobs left in running state."""
    return db.requeue_stale_jobs(stale_after_minutes)

def cleanup_temp_files():
    """Clean up expired input assets and temporary files older than 30 minutes."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # 1. Clean up expired database assets and their files
    try:
        expired_assets = db.delete_expired_assets()
        for asset in expired_assets:
            storage_kind = asset.get('storage_kind')
            locator = asset.get('storage_locator')
            if storage_kind in {'local', 'legacy_local', 'job_local'} and locator:
                storage_dir = 'assets' if storage_kind == 'local' else ('job_inputs' if storage_kind == 'job_local' else '')
                filepath = os.path.join(project_root, 'uploads', storage_dir, os.path.basename(locator))
                try:
                    if os.path.exists(filepath):
                        os.unlink(filepath)
                except OSError as e:
                    print(f"Error unlinking asset file {filepath}: {e}")
    except Exception as e:
        print(f"Asset cleanup error: {e}")

    # 2. Clean up temp PDFs directory (temp_pdfs)
    temp_pdfs_dir = os.path.join(project_root, 'uploads', 'temp_pdfs')
    if os.path.exists(temp_pdfs_dir):
        now = time.time()
        for filename in os.listdir(temp_pdfs_dir):
            filepath = os.path.join(temp_pdfs_dir, filename)
            try:
                if os.path.isfile(filepath) and os.path.getmtime(filepath) < now - 1800:
                    os.unlink(filepath)
            except OSError as e:
                print(f"Error unlinking temp pdf file {filepath}: {e}")
