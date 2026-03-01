import dotenv
import os
import requests
dotenv.load_dotenv()
from sheets_db import SheetsDB
db = SheetsDB()
db.connect()

try:
    parent_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID')
    print(f"Using parent ID: {parent_id}")
    
    # Try to create 'Test Folder' inside parent
    root_folder_id = db._find_or_create_folder('Test Quota Bypass', parent_id=parent_id)
    print("Folder created/found:", root_folder_id)
    
    if root_folder_id:
        headers = db._get_auth_header()
        files = {
            'metadata': ('', '{"name": "test.pdf", "parents": ["' + root_folder_id + '"], "mimeType": "application/pdf"}', 'application/json'),
            'file': ('test.pdf', b'hello test bypass quota', 'application/pdf')
        }
        r = requests.post("https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id,webViewLink", headers=headers, files=files)
        print("Upload Status:", r.status_code)
        print("Upload Response:", r.text)

except Exception as e:
    print('Error:', e)
