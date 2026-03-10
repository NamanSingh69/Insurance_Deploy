import os
from dotenv import load_dotenv
load_dotenv(override=True)
import json
import uuid
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
import requests
from google.oauth2.service_account import Credentials

SCOPE = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

class PostgresDB:
    def __init__(self):
        self.conn = None
        self.creds = None

    def connect(self):
        DATABASE_URL = os.getenv("DATABASE_URL")
        if not DATABASE_URL:
            # We don't want to crash on import if it's missing, just print warning
            print("Warning: DATABASE_URL not found.")
            return

        self.conn = psycopg2.connect(DATABASE_URL)
        self.conn.autocommit = True
        self._init_db()

        # Connect Drive API
        creds_json = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
        if creds_json:
            try:
                creds_dict = json.loads(creds_json)
                self.creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPE)
            except Exception as e:
                print(f"Error initializing Google Drive credentials: {e}")

    def _init_db(self):
        with self.conn.cursor() as cur:
            # Create Users Table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(255) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    full_name VARCHAR(255),
                    qualifications VARCHAR(255),
                    designation VARCHAR(255),
                    license_no VARCHAR(255),
                    expiry_date VARCHAR(255),
                    membership_no VARCHAR(255),
                    address_line_1 VARCHAR(255),
                    address_line_2 VARCHAR(255),
                    address_line_3 VARCHAR(255),
                    contact_no VARCHAR(255),
                    email VARCHAR(255)
                );
            """)
            
            # Create Reports Table - Note id is UUID and payload is JSONB natively!
            cur.execute("""
                CREATE TABLE IF NOT EXISTS reports (
                    id VARCHAR(255) PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id),
                    report_no TEXT,
                    insured_name TEXT,
                    vehicle_no TEXT,
                    claim_no TEXT,
                    policy_no TEXT,
                    saved_at TIMESTAMP,
                    include_in_consolidated BOOLEAN DEFAULT TRUE,
                    report_data_json JSONB
                );
            """)

    # --- User Methods ---
    def get_user_by_username(self, username):
        if not self.conn: self.connect()
        if not self.conn: return None # Still none after trying
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM users WHERE username = %s;", (username,))
                return cur.fetchone()
        except Exception as e:
             print(f"Error fetching user by username: {e}")
             return None

    def get_user_by_id(self, user_id):
        if not self.conn: self.connect()
        if not self.conn: return None
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM users WHERE id = %s;", (user_id,))
                return cur.fetchone()
        except Exception as e:
             print(f"Error fetching user by id: {e}")
             return None

    def create_user(self, user_data):
        if not self.conn: self.connect()
        if not self.conn: return None
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO users (
                        username, password_hash, full_name, qualifications, designation,
                        license_no, expiry_date, membership_no, address_line_1,
                        address_line_2, address_line_3, contact_no, email
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;
                """, (
                    user_data.get('username'), user_data.get('password_hash'),
                    user_data.get('full_name'), user_data.get('qualifications'),
                    user_data.get('designation'), user_data.get('license_no'),
                    user_data.get('expiry_date'), user_data.get('membership_no'),
                    user_data.get('address_line_1'), user_data.get('address_line_2'),
                    user_data.get('address_line_3'), user_data.get('contact_no'),
                    user_data.get('email')
                ))
                return cur.fetchone()[0]
        except Exception as e:
             print(f"Error creating user: {e}")
             return None

    # --- Report Methods ---
    def get_user_reports_metadata_only(self, user_id):
        """Fetches only metadata columns, skipping the heavy JSON data."""
        if not self.conn: self.connect()
        if not self.conn: return []
        out = []
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                # We specifically avoid SELECT * to prevent fetching the huge report_data_json in the list view
                cur.execute("""
                    SELECT id, user_id, report_no, insured_name, vehicle_no, claim_no, policy_no, saved_at, include_in_consolidated 
                    FROM reports WHERE user_id = %s ORDER BY saved_at DESC;
                """, (user_id,))
                for row in cur.fetchall():
                    row_dict = dict(row)
                    row_dict['id'] = str(row_dict['id'])
                    row_dict['saved_at'] = str(row_dict['saved_at']) if row_dict['saved_at'] else ''
                    out.append(row_dict)
            return out
        except Exception as e:
             print(f"Error getting reports metadata: {e}")
             return []

    def get_user_reports(self, user_id):
        """Fetches full reports for a user."""
        if not self.conn: self.connect()
        if not self.conn: return []
        out = []
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM reports WHERE user_id = %s ORDER BY saved_at DESC;", (user_id,))
                for row in cur.fetchall():
                     row_dict = dict(row)
                     row_dict['id'] = str(row_dict['id'])
                     row_dict['saved_at'] = str(row_dict['saved_at']) if row_dict['saved_at'] else ''
                     if isinstance(row_dict['report_data_json'], dict):
                          row_dict['report_data_json'] = json.dumps(row_dict['report_data_json'])
                     out.append(row_dict)
            return out
        except Exception as e:
             print(f"Error getting user reports: {e}")
             return []

    def save_report(self, user_id, report_data_dict):
        """Saves a report to PostgreSQL natively as JSONB!"""
        if not self.conn: self.connect()
        if not self.conn: return None
        try:
            report_no = str(report_data_dict.get('survey_report', {}).get('report_no', ''))
            insured_name = str(report_data_dict.get('survey_report', {}).get('insured', ''))
            vehicle_no = str(report_data_dict.get('survey_report', {}).get('vehicle_regn_no', ''))
            claim_no = str(report_data_dict.get('survey_report', {}).get('claim_no', ''))
            policy_no = str(report_data_dict.get('survey_report', {}).get('policy_no', ''))
            saved_at = datetime.utcnow()
            
            # Postgres JSONB handles the dict directly without us needing to chunk it manually
            report_data_json = json.dumps(report_data_dict)

            with self.conn.cursor() as cur:
                # Check if it exists for updates
                cur.execute("SELECT id FROM reports WHERE user_id = %s AND report_no = %s;", (user_id, report_no))
                existing = cur.fetchone()
                
                if existing:
                    report_id = existing[0]
                    cur.execute("""
                        UPDATE reports SET
                            insured_name = %s, vehicle_no = %s, claim_no = %s,
                            policy_no = %s, saved_at = %s, report_data_json = %s::jsonb
                        WHERE id = %s RETURNING id;
                    """, (insured_name, vehicle_no, claim_no, policy_no, saved_at, report_data_json, report_id))
                    return cur.fetchone()[0]
                else:
                    new_id = str(uuid.uuid4())
                    cur.execute("""
                        INSERT INTO reports (
                            id, user_id, report_no, insured_name, vehicle_no, claim_no, 
                            policy_no, saved_at, include_in_consolidated, report_data_json
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb) RETURNING id;
                    """, (new_id, user_id, report_no, insured_name, vehicle_no, claim_no, policy_no, saved_at, True, report_data_json))
                    return cur.fetchone()[0]
        except Exception as e:
             print(f"Error saving report: {e}")
             return None

    def delete_report(self, report_id, user_id):
        """Deletes a report."""
        if not self.conn: self.connect()
        if not self.conn: return False
        try:
            with self.conn.cursor() as cur:
                cur.execute("DELETE FROM reports WHERE id = %s AND user_id = %s RETURNING id;", (report_id, user_id))
                return cur.fetchone() is not None
        except Exception as e:
             print(f"Error deleting report: {e}")
             return False

    # --- Drive Methods (Unchanged, relies on Google Auth) ---
    def get_resumable_upload_url(self, filename, mime_type='application/pdf'):
        result = self.get_resumable_upload_url_with_token(filename, mime_type)
        return result['url'] if result else None
    
    def get_resumable_upload_url_with_token(self, filename, mime_type='application/pdf'):
        if not self.creds: self.connect()
        try:
            from google.auth.transport.requests import Request
            if not self.creds.valid:
                self.creds.refresh(Request())

            access_token = self.creds.token
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json',
                'X-Upload-Content-Type': mime_type,
            }
            metadata = {
                'name': filename,
                'mimeType': mime_type
            }
            
            drive_folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID')
            if drive_folder_id:
                metadata['parents'] = [drive_folder_id]
            
            response = requests.post(
                'https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable',
                headers=headers,
                json=metadata
            )
            
            if response.status_code == 200:
                upload_url = response.headers.get('Location')
                return {'url': upload_url, 'access_token': access_token}
            else:
                return None
        except Exception as e:
             return None

    def _get_auth_header(self):
        if not self.creds: self.connect()
        from google.auth.transport.requests import Request
        if not self.creds.valid:
            self.creds.refresh(Request())
        return {'Authorization': f'Bearer {self.creds.token}'}

    def get_file_content(self, file_id):
        try:
            headers = self._get_auth_header()
            url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return response.content
            return None
        except Exception as e:
             return None

    def upload_image_to_drive(self, file_content, filename, mime_type='image/jpeg'):
        try:
            headers = self._get_auth_header()
            file_metadata = {'name': filename}
            drive_folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID')
            if drive_folder_id:
                file_metadata['parents'] = [drive_folder_id]

            files = {
                'metadata': ('', json.dumps(file_metadata), 'application/json'),
                'file': (filename, file_content, mime_type)
            }
            
            upload_url = "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id,webViewLink,webContentLink"
            response = requests.post(upload_url, headers=headers, files=files)
            
            if response.status_code in [200, 201]:
                file_info = response.json()
                file_id = file_info.get('id')
                perm_url = f"https://www.googleapis.com/drive/v3/files/{file_id}/permissions"
                perm_data = {'type': 'anyone', 'role': 'reader'}
                requests.post(perm_url, headers=headers, json=perm_data)
                
                return {
                    'id': file_id,
                    'view_link': file_info.get('webViewLink'),
                    'download_link': file_info.get('webContentLink')
                }
            return None
        except Exception as e:
             return None

    def _find_or_create_folder(self, folder_name, parent_id=None):
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
                if files: return files[0]['id']
            
            metadata = {'name': folder_name, 'mimeType': 'application/vnd.google-apps.folder'}
            if parent_id: metadata['parents'] = [parent_id]
            
            create_response = requests.post(search_url, headers=headers, json=metadata)
            if create_response.status_code in [200, 201]:
                return create_response.json().get('id')
            return None
        except Exception as e:
             return None

    def upload_report_pdf(self, pdf_bytes, filename, vehicle_no):
        try:
            root_folder_id = self._find_or_create_folder('Survey Reports')
            if not root_folder_id: return None
            
            folder_name = "".join(c for c in vehicle_no if c.isalnum() or c in ('_', '-', ' ')).strip() if vehicle_no else 'Unknown_Vehicle'
            vehicle_folder_id = self._find_or_create_folder(folder_name, root_folder_id)
            if not vehicle_folder_id: return None
            
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
                file_id = existing_files[0]['id']
                files_multipart = {
                     'metadata': ('', json.dumps({}), 'application/json'),
                     'file': (filename, pdf_bytes, 'application/pdf')
                }
                update_url = f"https://www.googleapis.com/upload/drive/v3/files/{file_id}?uploadType=multipart&fields=id,webViewLink"
                response = requests.patch(update_url, headers=headers, files=files_multipart)
                if response.status_code in [200, 201]:
                    return response.json().get('webViewLink', f"https://drive.google.com/file/d/{file_id}/view")
            else:
                upload_url = "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id,webViewLink"
                response = requests.post(upload_url, headers=headers, files=files_multipart)
                if response.status_code in [200, 201]:
                    return response.json().get('webViewLink', f"https://drive.google.com/file/d/{response.json().get('id')}/view")
            return None
        except Exception as e:
             return None

db = PostgresDB()
