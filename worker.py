# worker.py
import os
import json
import socket
import time
import uuid
import logging
from datetime import datetime, timedelta
from db import db
from modules.assets import get_owned_asset_content, store_private_bytes
from modules.credentials import get_user_gemini_key
from modules.drive import DriveAuthorizationError, is_drive_connected, upload_report_to_personal_drive
from modules.gemini import execute_gemini_task
from modules.pdf import render_report
from modules.jobs import fail_job, complete_job, claim_next_job, requeue_stale_jobs, cleanup_temp_files

POLL_INTERVAL_SECONDS = float(os.getenv('JOB_POLL_INTERVAL_SECONDS', '1'))
WORKER_ID = os.getenv('JOB_WORKER_ID', f'{socket.gethostname()}-{os.getpid()}')
MAX_ATTEMPTS = 3
logger = logging.getLogger(__name__)

def _job_input(job):
    payload = job.get('input_json') or {}
    if isinstance(payload, str):
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            return {}
    return payload

def handle_job_failure(job, error_message):
    job_id = job['id']
    attempts = job.get('attempts', 1)
    
    created_at = job.get('created_at')
    queue_age = 0.0
    if created_at:
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at)
            except ValueError:
                created_at = None
        if isinstance(created_at, datetime):
            queue_age = (datetime.now() - created_at).total_seconds()
            
    print(f"[JOB-FAILED] Job {job_id} ({job['kind']}) failed on attempt {attempts}/{MAX_ATTEMPTS}. Queue age: {queue_age:.2f}s. Error: {error_message}")
    
    if attempts < MAX_ATTEMPTS:
        print(f"[JOB-RETRY] Requeuing job {job_id} for next attempt.")
        db.requeue_job(job_id)
    else:
        print(f"[JOB-FATAL] Job {job_id} exceeded maximum retry attempts. Marking as failed.")
        fail_job(job_id, error_message)

def _run_process_pdf(job, payload, user_data):
    job_id = job['id']
    user_id = job['user_id']
    kind = job['kind']
    
    mime_type = payload.get('mime_type', 'application/pdf')
    is_invoice = (kind == 'process_invoice')
    
    # 1. Fetch content from an application-owned private asset.  The browser
    # never submits provider file URIs or access capabilities to the worker.
    if payload.get('source_asset_id'):
        content, asset = get_owned_asset_content(payload['source_asset_id'], user_id)
        if not content:
            raise ValueError("The uploaded PDF is no longer available. Please upload it again.")
        pdf_part = {'mime_type': mime_type, 'data': content}
    else:
        raise ValueError("The processing job has no valid PDF input.")

    # 2. Setup Gemini Credentials
    api_key = get_user_gemini_key(user_data) or os.getenv("GEMINI_API_KEY")
    user_model = user_data.get('gemini_model')

    # 3. Execute Gemini Task
    result = execute_gemini_task(
        api_key=api_key,
        pdf_part=pdf_part,
        user_model=user_model,
        is_invoice=is_invoice
    )

    # 4. Apply Monolith Post-Process Defaults (for full survey reports only)
    if not is_invoice:
        survey_data = result.get('survey_report', {})
        if not survey_data.get('vehicle_pre_accident_condition'): 
            survey_data['vehicle_pre_accident_condition'] = "Average"
        if not survey_data.get('dl_endorsement'): 
            survey_data['dl_endorsement'] = "Not Known"
        if not survey_data.get('police_reported_to'): 
            survey_data['police_reported_to'] = "Not Reported"
        if not survey_data.get('police_diary_case_no'): 
            survey_data['police_diary_case_no'] = "N/A"
        if not survey_data.get('tp_details'): 
            survey_data['tp_details'] = "No ( As Per Claim Form )"
        if not survey_data.get('damages_extent'): 
            survey_data['damages_extent'] = "The Spare Parts which are included in Assessment column, found pressed/deformed/torn/ distorted &/or broken."
        if not survey_data.get('remark'): 
            survey_data['remark'] = "The declaration of the accident appeared consistent with the nature of the damages sustained"
        
        # Inject Last Saved Surveyor Details
        last_surveyor_details = db.get_last_surveyor_details(user_id)
        if last_surveyor_details:
            if 'assessment' in result:
                if 'page3_details' not in result['assessment']:
                    result['assessment']['page3_details'] = {}
                result['assessment']['page3_details']['surveyor_details'] = last_surveyor_details

    # 5. Complete Job
    complete_job(job_id, result)

def _run_generate_files(job, payload, user_data):
    job_id = job['id']
    user_id = job['user_id']
    
    report_data = payload.get('report_data')
    if not isinstance(report_data, dict):
        raise ValueError("The report-generation job has invalid input.")

    # 1. Render PDF Report
    render_result = render_report(report_data, user_data, user_id)
    pdf_bytes = render_result["pdf_bytes"]
    report_no = render_result["report_no"]
    vehicle_no = render_result["vehicle_no"]
    drive_link = render_result["drive_link"]
    filename_base = "".join(c for c in vehicle_no if c.isalnum() or c in ('_', '-')).rstrip() or "SurveyReport"
    filename = f"{filename_base}.pdf"
    if is_drive_connected(user_id):
        try:
            folder_name = "".join(c for c in vehicle_no if c.isalnum() or c in ('_', '-', ' ')).strip() or "Unknown Vehicle"
            drive_link = upload_report_to_personal_drive(user_id, pdf_bytes, filename, folder_name)
        except DriveAuthorizationError:
            # The report is still available through its private application
            # asset and the existing service-account fallback.
            logger.warning("Could not deliver generated report to connected Drive for user %s", user_id)

    # 2. Keep the downloadable copy in private storage for 30 minutes.
    generated_asset = store_private_bytes(
        user_id, pdf_bytes, filename, "application/pdf", "generated_report",
        expires_at=datetime.utcnow() + timedelta(minutes=30),
    )
    request_id = str(uuid.uuid4())

    # 3. Complete Job with metadata only; no document bytes live in the job row.
    complete_job(job_id, {
        "request_id": request_id,
        "asset_id": generated_asset["id"],
        "drive_link": drive_link,
        "report_no": report_no,
        "vehicle_no": vehicle_no
    })

def run_job(job):
    job_id = job['id']
    print(f"[JOB-STARTED] Running job {job_id} ({job['kind']}) for user {job['user_id']}")
    try:
        payload = _job_input(job)
        user_data = db.get_user_by_id(job['user_id'])
        if not user_data:
            raise ValueError("The job owner no longer exists.")
            
        if job['kind'] in ('process_pdf', 'process_invoice'):
            _run_process_pdf(job, payload, user_data)
        elif job['kind'] == 'generate_files':
            _run_generate_files(job, payload, user_data)
        else:
            raise ValueError(f"Unknown job type: {job['kind']}")
            
        print(f"[JOB-COMPLETED] Job {job_id} finished successfully.")
    except Exception as e:
        logger.exception("Job %s (%s) failed", job_id, job.get('kind'))
        handle_job_failure(job, "The background task could not be completed. Please try again.")

def main():
    print(f"[WORKER-STARTUP] Worker ID: {WORKER_ID}. Initializing DB connection pool.")
    db.connect()
    
    print("[WORKER-STARTUP] Performing startup stale jobs requeue.")
    try:
        requeue_stale_jobs()
    except Exception as e:
        print(f"Startup requeue error: {e}")
        
    last_cleanup_time = time.time()
    last_requeue_time = time.time()

    print("[WORKER-RUNNING] Polling queue for jobs...")
    while True:
        try:
            job = claim_next_job(WORKER_ID)
            if job:
                run_job(job)
                continue
        except Exception as e:
            print(f"Error checking/claiming job: {e}")

        now = time.time()
        # Clean up files older than 30 minutes every 5 minutes
        if now - last_cleanup_time > 300:
            print("[PERIODIC-CLEANUP] Running temporary files cleanup.")
            try:
                cleanup_temp_files()
            except Exception as exc:
                print(f"[PERIODIC-CLEANUP-ERROR] temporary files cleanup failed: {exc}")
            last_cleanup_time = now

        # Reclaim orphaned stale running jobs every 5 minutes
        if now - last_requeue_time > 300:
            print("[PERIODIC-REQUEUE] Checking for stale/abandoned running jobs.")
            try:
                requeue_stale_jobs()
            except Exception as exc:
                print(f"[PERIODIC-REQUEUE-ERROR] Requeue of stale jobs failed: {exc}")
            last_requeue_time = now

        time.sleep(POLL_INTERVAL_SECONDS)

if __name__ == '__main__':
    main()
