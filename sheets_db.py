import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json
from datetime import datetime
import uuid
import base64
import io
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
import requests
import math

# Google Sheets has a 50,000 character limit per cell
# We use 45,000 to be safe and account for potential encoding overhead
MAX_CELL_CHARS = 45000
MAX_JSON_CHUNKS = 5  # Maximum number of chunks (J, K, L, M, N columns)

# Scope required for accessing Google Sheets and Drive
SCOPE = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

class SheetsDB:
    def __init__(self):
        self.client = None
        self.sheet = None
        self.users_worksheet = None
        self.reports_worksheet = None
        self.drive_service = None
        self.creds = None

    def connect(self):
        """Connects to Google Sheets using credentials from environment."""
        creds_json = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
        if not creds_json:
            print("Warning: GOOGLE_SHEETS_CREDENTIALS not found.")
            return

        try:
            creds_dict = json.loads(creds_json)
            self.creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
            self.client = gspread.authorize(self.creds)
            
            # Build Drive Service
            self.drive_service = build('drive', 'v3', credentials=self.creds)
            
            # Open the spreadsheet (assumes name is 'InsuranceAppDB' by default, or env var)
            sheet_name = os.getenv("GOOGLE_SHEET_NAME", "InsuranceAppDB")
            try:
                self.sheet = self.client.open(sheet_name)
            except gspread.SpreadsheetNotFound:
                # If not found, try to create it (only works if service account has permission to create, 
                # usually it's better to share an existing sheet)
                print(f"Spreadsheet '{sheet_name}' not found. Please create it and share with service account.")
                raise

            # Get or Create Worksheets
            try:
                self.users_worksheet = self.sheet.worksheet("Users")
            except gspread.WorksheetNotFound:
                self.users_worksheet = self.sheet.add_worksheet(title="Users", rows=100, cols=20)
                # Add Header
                self.users_worksheet.append_row([
                    "id", "username", "password_hash", "full_name", "qualifications", 
                    "designation", "license_no", "expiry_date", "membership_no", 
                    "address_line_1", "address_line_2", "address_line_3", 
                    "contact_no", "email"
                ])

            try:
                self.reports_worksheet = self.sheet.worksheet("Reports")
            except gspread.WorksheetNotFound:
                # cols=15 to accommodate JSON chunks (J, K, L, M, N)
                self.reports_worksheet = self.sheet.add_worksheet(title="Reports", rows=100, cols=15)
                self.reports_worksheet.append_row([
                    "id", "user_id", "report_no", "insured_name", "vehicle_no", 
                    "claim_no", "policy_no", "saved_at", "include_in_consolidated", 
                    "report_data_json", "report_data_json_2", "report_data_json_3", 
                    "report_data_json_4", "report_data_json_5"
                ])

        except Exception as e:
            print(f"Error connecting to Google Sheets: {e}")
            raise

    # --- User Methods ---
    def get_user_by_username(self, username):
        if not self.users_worksheet: self.connect()
        try:
            # cell = self.users_worksheet.find(username) # Find by cell content (might be slow or find partial matches)
            # Safer to fetch all records and filter
            records = self.users_worksheet.get_all_records()
            for record in records:
                if record['username'] == username:
                    return record
            return None
        except Exception as e:
            print(f"Error fetching user: {e}")
            return None

    def get_user_by_id(self, user_id):
        if not self.users_worksheet: self.connect()
        try:
            records = self.users_worksheet.get_all_records()
            for record in records:
                if str(record['id']) == str(user_id):
                    return record
            return None
        except Exception as e:
            print(f"Error fetching user by id: {e}")
            return None

    def create_user(self, user_data):
        if not self.users_worksheet: self.connect()
        # Generate ID (simple auto-increment simulation or uuid)
        # Using numeric ID to match legacy SQLite model structure if possible, but UUID is safer for concurrent sheets
        # For simplicity, let's use a random integer or existing length + 1
        new_id = len(self.users_worksheet.col_values(1))  # 1-based, header is 1, so len is next id if dense
        
        row = [
            new_id, user_data.get('username'), user_data.get('password_hash'),
            user_data.get('full_name'), user_data.get('qualifications'),
            user_data.get('designation'), user_data.get('license_no'),
            user_data.get('expiry_date'), user_data.get('membership_no'),
            user_data.get('address_line_1'), user_data.get('address_line_2'),
            user_data.get('address_line_3'), user_data.get('contact_no'),
            user_data.get('email')
        ]
        self.users_worksheet.append_row(row)
        return new_id

    # --- Drive Methods ---
    def get_resumable_upload_url(self, filename, mime_type='application/pdf'):
        """
        Generates a resumable upload session URL for direct frontend upload.
        """
        result = self.get_resumable_upload_url_with_token(filename, mime_type)
        return result['url'] if result else None
    
    def get_resumable_upload_url_with_token(self, filename, mime_type='application/pdf'):
        """
        Generates a resumable upload session URL and returns it with the access token.
        """
        if not self.creds: self.connect()
        try:
            import httplib2
            # Ensure token is fresh
            if self.creds.access_token_expired or not self.creds.access_token:
                self.creds.refresh(httplib2.Http())

            access_token = self.creds.access_token
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json',
                'X-Upload-Content-Type': mime_type,
            }
            
            metadata = {
                'name': filename,
                'mimeType': mime_type
            }
            
            # Use shared folder if configured (required for service account quota)
            drive_folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID')
            print(f"DEBUG: GOOGLE_DRIVE_FOLDER_ID = '{drive_folder_id}'")
            if drive_folder_id:
                metadata['parents'] = [drive_folder_id]
                print(f"DEBUG: Uploading to folder: {drive_folder_id}")
            else:
                print("DEBUG: No folder ID set, uploading to root (will fail for service accounts)")
            
            print(f"DEBUG: Upload metadata = {metadata}")
            
            response = requests.post(
                'https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable',
                headers=headers,
                json=metadata
            )
            
            if response.status_code == 200:
                upload_url = response.headers.get('Location')
                return {'url': upload_url, 'access_token': access_token}
            else:
                print(f"Failed to initiate resumable upload: {response.text}")
                return None

        except Exception as e:
            print(f"Error getting resumable upload URL: {e}")
            return None

    def get_file_content(self, file_id):
        """Downloads file content as bytes from Drive."""
        if not self.drive_service: self.connect()
        try:
            request = self.drive_service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            return fh.getvalue()
        except Exception as e:
            print(f"Error downloading file {file_id}: {e}")
            return None

    def upload_image_to_drive(self, file_content, filename, mime_type='image/jpeg'):
        """Uploads an image to Google Drive and returns the webViewLink."""
        if not self.drive_service: self.connect()
        try:
            file_metadata = {
                'name': filename,
                'mimeType': mime_type
            }
            
            # Use shared folder if configured (required for service account quota)
            drive_folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID')
            if drive_folder_id:
                file_metadata['parents'] = [drive_folder_id]
            
            # Create media upload
            fh = io.BytesIO(file_content)
            media = MediaIoBaseUpload(fh, mimetype=mime_type, resumable=True)
            
            file = self.drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink, webContentLink'
            ).execute()
            
            # Make file readable by anyone with the link (so frontend can display it)
            # Alternatively, we could just rely on Service Account if we proxied, but direct link is requested.
            # IMPORTANT: This makes the image public to anyone with the link.
            permission = {
                'type': 'anyone',
                'role': 'reader',
            }
            self.drive_service.permissions().create(
                fileId=file.get('id'),
                body=permission,
                fields='id',
            ).execute()
            
            return {
                'id': file.get('id'),
                'view_link': file.get('webViewLink'),
                'download_link': file.get('webContentLink') # Use this for embedding in PDF if needed
            }
            
        except Exception as e:
            print(f"Error uploading to Drive: {e}")
            return None

    # --- Report Methods ---
    def _chunk_json_data(self, json_string):
        """
        Splits a JSON string into chunks that fit within Google Sheets' cell limit.
        Returns a list of chunks.
        """
        if len(json_string) <= MAX_CELL_CHARS:
            return [json_string]
        
        chunks = []
        for i in range(0, len(json_string), MAX_CELL_CHARS):
            chunks.append(json_string[i:i + MAX_CELL_CHARS])
        
        if len(chunks) > MAX_JSON_CHUNKS:
            raise ValueError(f"Report data too large: requires {len(chunks)} chunks, max is {MAX_JSON_CHUNKS}")
        
        return chunks
    
    def _reassemble_json_chunks(self, chunks):
        """
        Reassembles JSON chunks back into a single JSON string.
        Chunks is a list of strings (may contain empty strings for padding).
        """
        return ''.join([c for c in chunks if c])

    def save_report(self, user_id, report_data_dict):
        if not self.reports_worksheet: self.connect()
        
        # Fix: report_no is inside survey_report, not at top level
        report_no = report_data_dict.get('survey_report', {}).get('report_no', '')
        json_data = json.dumps(report_data_dict)
        
        # Chunk the JSON data to fit within cell limits
        try:
            json_chunks = self._chunk_json_data(json_data)
            print(f"DEBUG: JSON size = {len(json_data)}, chunks = {len(json_chunks)}")
        except ValueError as e:
            raise ValueError(f"Report data too large to save: {e}")
        
        # Pad chunks to always have MAX_JSON_CHUNKS elements
        while len(json_chunks) < MAX_JSON_CHUNKS:
            json_chunks.append('')
        
        # Check if exists to update
        records = self.reports_worksheet.get_all_records()
        row_idx_to_update = None
        
        for idx, record in enumerate(records):
            # Fix: Ensure strict string comparison for User ID and Report No to avoid duplicates
            if str(record.get('user_id', '')) == str(user_id) and str(record.get('report_no', '')).strip() == str(report_no).strip():
                row_idx_to_update = idx + 2 # +2 because 1-based index and header row
                break
        
        saved_at = datetime.utcnow().isoformat()
        
        if row_idx_to_update:
            # Update existing - preserve the original ID
            original_id = records[row_idx_to_update - 2]['id']
            row_data = [
                 original_id, user_id, report_no,
                 report_data_dict.get('survey_report', {}).get('insured', ''),
                 report_data_dict.get('survey_report', {}).get('vehicle_regn_no', ''),
                 report_data_dict.get('survey_report', {}).get('claim_no', ''),
                 report_data_dict.get('survey_report', {}).get('policy_no', ''),
                 saved_at,
                 False, # include_in_consolidated default
            ] + json_chunks  # Append all JSON chunks (columns J-N)
            
            # Update range: A to N (14 columns)
            rng = f"A{row_idx_to_update}:N{row_idx_to_update}"
            self.reports_worksheet.update(range_name=rng, values=[row_data])
            return original_id
            
        else:
            # Create New - Use UUID for concurrent-safe unique IDs
            new_id = str(uuid.uuid4())
            row_data = [
                 new_id, user_id, report_no,
                 report_data_dict.get('survey_report', {}).get('insured', ''),
                 report_data_dict.get('survey_report', {}).get('vehicle_regn_no', ''),
                 report_data_dict.get('survey_report', {}).get('claim_no', ''),
                 report_data_dict.get('survey_report', {}).get('policy_no', ''),
                 saved_at,
                 False,
            ] + json_chunks  # Append all JSON chunks (columns J-N)
            self.reports_worksheet.append_row(row_data)
            return new_id

    def get_user_reports(self, user_id):
        """Fetches full reports for a user, reassembling JSON chunks."""
        if not self.reports_worksheet: self.connect()
        try:
            records = self.reports_worksheet.get_all_records()
            user_reports = []
            for record in records:
                if str(record['user_id']) == str(user_id):
                    # Reassemble JSON chunks if they exist
                    json_chunks = [
                        record.get('report_data_json', ''),
                        record.get('report_data_json_2', ''),
                        record.get('report_data_json_3', ''),
                        record.get('report_data_json_4', ''),
                        record.get('report_data_json_5', '')
                    ]
                    # Combine chunks and update the record
                    full_json = self._reassemble_json_chunks(json_chunks)
                    record['report_data_json'] = full_json
                    user_reports.append(record)
            return user_reports
        except Exception as e:
            print(f"Error getting reports: {e}")
            return []

    def get_user_reports_metadata_only(self, user_id):
        """Fetches only metadata columns (A to I), skipping the heavy JSON data (Column J)."""
        if not self.reports_worksheet: self.connect()
        try:
            # Metadata columns: id(A), user_id(B), report_no(C), insured_name(D), vehicle_no(E), 
            # claim_no(F), policy_no(G), saved_at(H), include_in_consolidated(I)
            # JSON Data is Column J. We fetch A:I.
            # get_values returns list of lists, including header.
            rows = self.reports_worksheet.get('A:I') 
            
            headers = rows[0]
            data_rows = rows[1:]
            
            user_reports = []
            for row in data_rows:
                # Row might be shorter than headers if empty cells at end
                # Ensure we have enough columns to check user_id (index 1)
                if len(row) > 1 and str(row[1]) == str(user_id):
                    # Construct dict manually or zip. 
                    # Row might not have all columns if empty, pad it.
                    record = {}
                    for i, header in enumerate(headers):
                        val = row[i] if i < len(row) else ''
                        record[header] = val
                    user_reports.append(record)
            return user_reports
        except Exception as e:
            print(f"Error getting metadata reports: {e}")
            return []

    def get_report_by_id(self, report_id):
         # Helper if needed
         pass

    def delete_report(self, report_id, user_id):
        """Deletes a report by ID and User ID."""
        if not self.reports_worksheet: self.connect()
        try:
            records = self.reports_worksheet.get_all_records()
            row_idx_to_delete = None
            
            # Find the row to delete
            for idx, record in enumerate(records):
                # Check both ID and User ID for security
                if str(record.get('id', '')) == str(report_id) and str(record.get('user_id', '')) == str(user_id):
                    row_idx_to_delete = idx + 2 # +2 because 1-based index and header row
                    break
            
            if row_idx_to_delete:
                self.reports_worksheet.delete_rows(row_idx_to_delete)
                print(f"Deleted report {report_id} at row {row_idx_to_delete}")
                return True
            else:
                print(f"Report {report_id} not found for deletion.")
                return False

        except Exception as e:
            print(f"Error deleting report: {e}")
            return False

db = SheetsDB()
