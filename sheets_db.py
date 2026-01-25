import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json
from datetime import datetime
import uuid

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

    def connect(self):
        """Connects to Google Sheets using credentials from environment."""
        creds_json = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
        if not creds_json:
            print("Warning: GOOGLE_SHEETS_CREDENTIALS not found.")
            return

        try:
            creds_dict = json.loads(creds_json)
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
            self.client = gspread.authorize(creds)
            
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
                self.reports_worksheet = self.sheet.add_worksheet(title="Reports", rows=100, cols=10)
                self.reports_worksheet.append_row([
                    "id", "user_id", "report_no", "insured_name", "vehicle_no", 
                    "claim_no", "policy_no", "saved_at", "include_in_consolidated", "report_data_json"
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

    # --- Report Methods ---
    def save_report(self, user_id, report_data_dict):
        if not self.reports_worksheet: self.connect()
        
        report_no = report_data_dict.get('report_no')
        json_data = json.dumps(report_data_dict)
        
        # Check if exists to update
        records = self.reports_worksheet.get_all_records()
        row_idx_to_update = None
        
        for idx, record in enumerate(records):
            if str(record['user_id']) == str(user_id) and record['report_no'] == report_no:
                row_idx_to_update = idx + 2 # +2 because 1-based index and header row
                break
        
        saved_at = datetime.utcnow().isoformat()
        
        if row_idx_to_update:
            # Update existing
            # Update specific cells or replace row. Replacing row is safer for column alignment
            # Columns: id, user_id, report_no, insured_name, vehicle_no, claim_no, policy_no, saved_at, include, json
            # We preserve the original ID
            original_id = records[row_idx_to_update - 2]['id']
            row_data = [
                 original_id, user_id, report_no,
                 report_data_dict.get('survey_report', {}).get('insured', ''),
                 report_data_dict.get('survey_report', {}).get('vehicle_regn_no', ''),
                 report_data_dict.get('survey_report', {}).get('claim_no', ''),
                 report_data_dict.get('survey_report', {}).get('policy_no', ''),
                 saved_at,
                 False, # include_in_consolidated default
                 json_data
            ]
            # gspread update range
            # A2:J2 example
            # This is complex to target exact cells dynamically efficiently. 
            # Simple approach: Delete old row, append new (Changes ID order/reference potential issues)
            # Better approach: Update the cells.
            
            # For this MVP, let's just append new and ignore old in 'get' logic? No, that bloats.
            # Let's use `update` with range.
            rng = f"A{row_idx_to_update}:J{row_idx_to_update}"
            self.reports_worksheet.update(range_name=rng, values=[row_data])
            return original_id
            
        else:
            # Create New
            new_id = len(self.reports_worksheet.col_values(1))
            row_data = [
                 new_id, user_id, report_no,
                 report_data_dict.get('survey_report', {}).get('insured', ''),
                 report_data_dict.get('survey_report', {}).get('vehicle_regn_no', ''),
                 report_data_dict.get('survey_report', {}).get('claim_no', ''),
                 report_data_dict.get('survey_report', {}).get('policy_no', ''),
                 saved_at,
                 False,
                 json_data
            ]
            self.reports_worksheet.append_row(row_data)
            return new_id

    def get_user_reports(self, user_id):
        # Optimization: Fetch full records is heavy. Keeping this for compatibility or specific needs.
        if not self.reports_worksheet: self.connect()
        try:
            records = self.reports_worksheet.get_all_records()
            user_reports = []
            for record in records:
                if str(record['user_id']) == str(user_id):
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

db = SheetsDB()
