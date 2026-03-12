import gspread
from google.oauth2.service_account import Credentials
import os
import json
from datetime import datetime
import uuid
import base64
import io
import requests
import math
import mimetypes
import math

# Google Sheets has a 50,000 character limit per cell
# We use 45,000 to be safe and account for potential encoding overhead
MAX_CELL_CHARS = 45000
MAX_JSON_CHUNKS = 1000  # Increased to 1000 to support very large reports with images

# ... (omitted SCOPE and init) ...


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
            self.creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPE)
            self.client = gspread.authorize(self.creds)
            
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
    def get_resumable_upload_url(self, filename, mime_type='application/pdf', origin=None):
        """
        Generates a resumable upload session URL for direct frontend upload.
        """
        result = self.get_resumable_upload_url_with_token(filename, mime_type, origin)
        return result['url'] if result else None
    
    def get_resumable_upload_url_with_token(self, filename, mime_type='application/pdf', origin=None):
        """
        Generates a resumable upload session URL and returns it with the access token.
        """
        if not self.creds: self.connect()
        try:
            from google.auth.transport.requests import Request
            # Ensure token is fresh
            if not self.creds.valid:
                self.creds.refresh(Request())

            access_token = self.creds.token
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json',
                'X-Upload-Content-Type': mime_type,
            }
            if origin:
                headers['Origin'] = origin
            
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

    def _get_auth_header(self):
        """Helper to get a fresh access token for REST API calls."""
        if not self.creds: self.connect()
        from google.auth.transport.requests import Request
        if not self.creds.valid:
            self.creds.refresh(Request())
        return {'Authorization': f'Bearer {self.creds.token}'}

    def get_file_content(self, file_id):
        """Downloads file content as bytes from Drive."""
        try:
            headers = self._get_auth_header()
            url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return response.content
            else:
                print(f"Error downloading file {file_id}: [{response.status_code}] {response.text}")
                return None
        except Exception as e:
            print(f"Error downloading file {file_id}: {e}")
            return None

    def upload_image_to_drive(self, file_content, filename, mime_type='image/jpeg'):
        """Uploads an image to Google Drive and returns the webViewLink."""
        try:
            headers = self._get_auth_header()
            
            file_metadata = {'name': filename}
            drive_folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID')
            if drive_folder_id:
                file_metadata['parents'] = [drive_folder_id]

            # Multipart upload
            files = {
                'metadata': ('', json.dumps(file_metadata), 'application/json'),
                'file': (filename, file_content, mime_type)
            }
            
            upload_url = "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id,webViewLink,webContentLink"
            response = requests.post(upload_url, headers=headers, files=files)
            
            if response.status_code in [200, 201]:
                file_info = response.json()
                file_id = file_info.get('id')
                
                # Make file readable by anyone with the link
                perm_url = f"https://www.googleapis.com/drive/v3/files/{file_id}/permissions"
                perm_data = {'type': 'anyone', 'role': 'reader'}
                requests.post(perm_url, headers=headers, json=perm_data)
                
                return {
                    'id': file_id,
                    'view_link': file_info.get('webViewLink'),
                    'download_link': file_info.get('webContentLink')
                }
            else:
                print(f"Error uploading image to Drive: [{response.status_code}] {response.text}")
                return None
                
        except Exception as e:
            print(f"Error uploading to Drive: {e}")
            return None

    def _find_or_create_folder(self, folder_name, parent_id=None):
        """Finds a folder by name (under optional parent) or creates it. Returns folder ID."""
        try:
            headers = self._get_auth_header()
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            if parent_id:
                query += f" and '{parent_id}' in parents"
            
            search_url = f"https://www.googleapis.com/drive/v3/files"
            params = {'q': query, 'fields': 'files(id,name)', 'spaces': 'drive'}
            
            response = requests.get(search_url, headers=headers, params=params)
            if response.status_code == 200:
                files = response.json().get('files', [])
                if files:
                    return files[0]['id']
            
            # Create the folder
            metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            if parent_id:
                metadata['parents'] = [parent_id]
            
            create_response = requests.post(search_url, headers=headers, json=metadata)
            if create_response.status_code in [200, 201]:
                return create_response.json().get('id')
            return None
        except Exception as e:
            print(f"Error finding/creating folder '{folder_name}': {e}")
            return None

    def upload_report_pdf(self, pdf_bytes, filename, vehicle_no):
        """
        Uploads a report PDF to Drive: Survey Reports/{vehicle_no}/{filename}.
        Creates folders automatically. Replaces existing file if same name exists.
        Returns the web view link or None.
        """
        try:
            # 1. Find/create "Survey Reports" root folder
            root_folder_id = self._find_or_create_folder('Survey Reports')
            if not root_folder_id: return None
            
            # 2. Find/create vehicle subfolder
            folder_name = "".join(c for c in vehicle_no if c.isalnum() or c in ('_', '-', ' ')).strip() if vehicle_no else 'Unknown_Vehicle'
            vehicle_folder_id = self._find_or_create_folder(folder_name, root_folder_id)
            if not vehicle_folder_id: return None
            
            # 3. Check if file already exists
            headers = self._get_auth_header()
            query = f"name='{filename}' and '{vehicle_folder_id}' in parents and trashed=false"
            search_url = f"https://www.googleapis.com/drive/v3/files"
            params = {'q': query, 'fields': 'files(id,webViewLink)', 'spaces': 'drive'}
            
            search_response = requests.get(search_url, headers=headers, params=params)
            existing_files = []
            if search_response.status_code == 200:
                existing_files = search_response.json().get('files', [])

            files_multipart = {
                'metadata': ('', json.dumps({'name': filename, 'parents': [vehicle_folder_id], 'mimeType': 'application/pdf'}), 'application/json'),
                'file': (filename, pdf_bytes, 'application/pdf')
            }
            
            if existing_files:
                # Update existing file (PATCH)
                file_id = existing_files[0]['id']
                # For update, parents are NOT included in metadata normally, so let's strip it to be safe just in case
                files_multipart = {
                     'metadata': ('', json.dumps({}), 'application/json'),
                     'file': (filename, pdf_bytes, 'application/pdf')
                }
                update_url = f"https://www.googleapis.com/upload/drive/v3/files/{file_id}?uploadType=multipart&fields=id,webViewLink"
                response = requests.patch(update_url, headers=headers, files=files_multipart)
                if response.status_code in [200, 201]:
                    print(f"Updated report in Drive: Survey Reports/{folder_name}/{filename}")
                    return response.json().get('webViewLink', f"https://drive.google.com/file/d/{file_id}/view")
            else:
                # Create new file (POST)
                upload_url = "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id,webViewLink"
                response = requests.post(upload_url, headers=headers, files=files_multipart)
                if response.status_code in [200, 201]:
                    print(f"Uploaded report to Drive: Survey Reports/{folder_name}/{filename}")
                    return response.json().get('webViewLink', f"https://drive.google.com/file/d/{response.json().get('id')}/view")
            
            return None
        except Exception as e:
            print(f"Error uploading report PDF to Drive: {e}")
            import traceback; traceback.print_exc()
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

    def _reassemble_json_chunks(self, chunks):
        """
        Reassembles JSON chunks back into a single JSON string.
        Chunks is a list of strings (may contain empty strings for padding).
        """
        return ''.join([c for c in chunks if c])

    def save_report(self, user_id, report_data_dict):
        """Saves a report to the sheet, chunking the JSON data."""
        if not self.reports_worksheet: self.connect()

        # Extract report_no from data
        report_no = report_data_dict.get('survey_report', {}).get('report_no', '')
        
        # Ensure headers exist for all chunks (dynamic check to avoid get_all_records issues)
        try:
            headers = self.reports_worksheet.row_values(1)
            needed_headers_count = 9 + MAX_JSON_CHUNKS # A-I (9) + Chunks
            if len(headers) < needed_headers_count:
                # Add missing headers
                new_headers = []
                for i in range(len(headers) - 9, MAX_JSON_CHUNKS):
                    suffix = f"_{i+1}" if i > 0 else ""
                    new_headers.append(f"report_data_json{suffix}")
                
                if new_headers:
                    start_col_idx = len(headers) + 1
                    self.reports_worksheet.update(values=[new_headers], range_name=f"{self._col_idx_to_a1(start_col_idx)}1")
        except Exception as e:
            print(f"Warning: Could not check/update headers: {e}")

        json_string = json.dumps(report_data_dict)
        json_chunks = self._chunk_json_data(json_string)
        
        while len(json_chunks) < MAX_JSON_CHUNKS:
            json_chunks.append("")
            
        records = self.reports_worksheet.get_all_records()
        row_idx_to_update = None
        
        for idx, record in enumerate(records):
            if str(record.get('user_id', '')) == str(user_id) and str(record.get('report_no', '')).strip() == str(report_no).strip():
                row_idx_to_update = idx + 2
                break
        
        saved_at = datetime.utcnow().isoformat()
        
        if row_idx_to_update:
            original_id = records[row_idx_to_update - 2]['id']
            original_include = records[row_idx_to_update - 2].get('include_in_consolidated', True)

            row_data = [
                 original_id, user_id, report_no,
                 report_data_dict.get('survey_report', {}).get('insured', ''),
                 report_data_dict.get('survey_report', {}).get('vehicle_regn_no', ''),
                 report_data_dict.get('survey_report', {}).get('claim_no', ''),
                 report_data_dict.get('survey_report', {}).get('policy_no', ''),
                 saved_at,
                 original_include, 
            ] + json_chunks
            
            end_col = self._col_idx_to_a1(9 + MAX_JSON_CHUNKS)
            rng = f"A{row_idx_to_update}:{end_col}{row_idx_to_update}"
            self.reports_worksheet.update(range_name=rng, values=[row_data])
            return original_id
            
        else:
            new_id = str(uuid.uuid4())
            row_data = [
                 new_id, user_id, report_no,
                 report_data_dict.get('survey_report', {}).get('insured', ''),
                 report_data_dict.get('survey_report', {}).get('vehicle_regn_no', ''),
                 report_data_dict.get('survey_report', {}).get('claim_no', ''),
                 report_data_dict.get('survey_report', {}).get('policy_no', ''),
                 saved_at,
                 True, 
            ] + json_chunks
            self.reports_worksheet.append_row(row_data)
            return new_id

    def get_user_reports(self, user_id):
        """Fetches full reports for a user, reassembling JSON chunks."""
        if not self.reports_worksheet: self.connect()
        try:
            records = self.reports_worksheet.get_all_records()
            user_reports = []
            for record in records:
                if str(record.get('user_id')) == str(user_id):
                    json_chunks = []
                    json_chunks.append(record.get('report_data_json', ''))
                    for i in range(2, MAX_JSON_CHUNKS + 1):
                        key = f"report_data_json_{i}"
                        json_chunks.append(record.get(key, ''))
                        
                    full_json = self._reassemble_json_chunks(json_chunks)
                    if full_json:
                        pass
                    record['report_data_json'] = full_json
                    user_reports.append(record)
            return user_reports
        except Exception as e:
            print(f"Error getting reports: {e}")
            return []

    def _col_idx_to_a1(self, n):
        """Converts valid 1-based column index to A1 notation string."""
        string = ""
        while n > 0:
            n, remainder = divmod(n - 1, 26)
            string = chr(65 + remainder) + string
        return string

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
