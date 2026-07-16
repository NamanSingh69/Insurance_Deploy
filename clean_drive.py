#!/usr/bin/env python3
"""
clean_drive.py
Utility script to free up space in Google Drive Service Account.
Deletes files (e.g. photos, PDFs) older than a specified number of days.
"""

import os
import sys
import json
import argparse
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from google.oauth2.service_account import Credentials
import requests
from dotenv import load_dotenv

SCOPE = ['https://www.googleapis.com/auth/drive']

def get_auth_headers(creds_json):
    try:
        creds_dict = json.loads(creds_json)
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPE)
        from google.auth.transport.requests import Request
        creds.refresh(Request())
        return {'Authorization': f'Bearer {creds.token}'}
    except Exception as e:
        print(f"Error initializing Google Drive credentials: {e}")
        sys.exit(1)

def list_all_files(headers):
    files = []
    next_page_token = None
    print("Fetching list of all files in Google Drive...")
    while True:
        url = "https://www.googleapis.com/drive/v3/files?pageSize=1000&fields=nextPageToken,files(id,name,size,mimeType,createdTime)"
        if next_page_token:
            url += f"&pageToken={next_page_token}"
        
        resp = requests.get(url, headers=headers)
        if resp.status_code != 200:
            print(f"Error listing files: {resp.status_code} - {resp.text}")
            sys.exit(1)
            
        data = resp.json()
        files.extend(data.get('files', []))
        next_page_token = data.get('nextPageToken')
        if not next_page_token:
            break
            
    return files

def delete_file(file_id, filename, headers):
    url = f"https://www.googleapis.com/drive/v3/files/{file_id}"
    try:
        resp = requests.delete(url, headers=headers, timeout=10)
        if resp.status_code in [200, 204]:
            return True, None
        else:
            return False, f"HTTP {resp.status_code}: {resp.text[:100]}"
    except Exception as e:
        return False, str(e)

def main():
    parser = argparse.ArgumentParser(description="Clean up old files from Google Drive Service Account to free up space.")
    parser.add_argument("--days", type=int, default=30, help="Delete files older than this number of days (default: 30)")
    parser.add_argument("--dry-run", action="store_true", default=False, help="List files that would be deleted without deleting them")
    parser.add_argument("--no-confirm", action="store_true", default=False, help="Skip confirmation prompt before actual deletion")
    
    args = parser.parse_args()
    
    # Load env
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    load_dotenv(dotenv_path=env_path, override=True)
    
    creds_json = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
    if not creds_json:
        print("ERROR: GOOGLE_SHEETS_CREDENTIALS not found in environment (.env).")
        sys.exit(1)
        
    headers = get_auth_headers(creds_json)
    
    # Query storage usage first
    about_url = "https://www.googleapis.com/drive/v3/about?fields=storageQuota"
    about_resp = requests.get(about_url, headers=headers)
    if about_resp.status_code == 200:
        quota = about_resp.json().get('storageQuota', {})
        limit_bytes = int(quota.get('limit', 0))
        usage_bytes = int(quota.get('usage', 0))
        limit = limit_bytes / 1024 / 1024 / 1024
        usage = usage_bytes / 1024 / 1024 / 1024
        if limit > 0:
            print(f"Current Google Drive Quota: {usage:.2f} GB / {limit:.2f} GB ({(usage/limit)*100:.1f}% full)")
        else:
            print(f"Current Google Drive Quota: {usage:.2f} GB used (unlimited/no limit)")
    
    files = list_all_files(headers)
    print(f"Total files in Drive: {len(files)}")
    
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=args.days)
    print(f"Identifying files created before {cutoff_date.isoformat()} (older than {args.days} days)...")
    
    to_delete = []
    for f in files:
        # Keep folders and the main database spreadsheet
        if f.get('mimeType') == 'application/vnd.google-apps.folder':
            continue
        if f.get('mimeType') == 'application/vnd.google-apps.spreadsheet' or 'InsuranceAppDB' in f.get('name', ''):
            continue
            
        created_time_str = f.get('createdTime')
        if not created_time_str:
            continue
            
        # Parse timestamp: e.g. 2026-06-14T16:00:18.775Z
        created_time = datetime.strptime(created_time_str.replace('Z', '+00:00'), "%Y-%m-%dT%H:%M:%S.%f%z")
        
        if created_time < cutoff_date:
            to_delete.append(f)
            
    if not to_delete:
        print("No files matched the deletion criteria.")
        sys.exit(0)
        
    total_size_mb = sum(int(f.get('size', 0)) for f in to_delete) / 1024 / 1024
    print(f"\nFound {len(to_delete)} files to delete (total size: {total_size_mb:.2f} MB)")
    
    if args.dry_run:
        print("\n--- DRY RUN: The following files WOULD be deleted ---")
        for f in to_delete[:50]:
            print(f"- {f['name']} (ID: {f['id']}, Size: {int(f.get('size', 0))/1024/1024:.2f} MB, Created: {f['createdTime']})")
        if len(to_delete) > 50:
            print(f"... and {len(to_delete) - 50} more files")
        print("\nDry run completed. No files were deleted.")
        sys.exit(0)
        
    if not args.no_confirm:
        confirm = input(f"Are you sure you want to PERMANENTLY DELETE {len(to_delete)} files? (y/N): ").strip().lower()
        if confirm != 'y':
            print("Operation aborted.")
            sys.exit(0)
            
    print(f"\nDeleting {len(to_delete)} files concurrently...")
    success_count = 0
    failure_count = 0
    
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(delete_file, f['id'], f['name'], headers): f for f in to_delete}
        for future in as_completed(futures):
            f = futures[future]
            success, err = future.result()
            if success:
                success_count += 1
            else:
                failure_count += 1
                print(f"Failed to delete {f['name']} (ID: {f['id']}): {err}")
                
    print(f"\nDeletion completed: {success_count} succeeded, {failure_count} failed.")
    
    # Query storage usage again
    about_resp = requests.get(about_url, headers=headers)
    if about_resp.status_code == 200:
        quota = about_resp.json().get('storageQuota', {})
        usage = int(quota.get('usage', 0)) / 1024 / 1024 / 1024
        print(f"Updated Google Drive Quota Usage: {usage:.2f} GB")

if __name__ == "__main__":
    main()
