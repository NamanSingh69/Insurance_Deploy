import os
import json
import requests
from app import app

def upload_to_gemini(upload_url, filepath):
    CHUNK_SIZE = 8 * 1024 * 1024
    file_size = os.path.getsize(filepath)
    gemini_file_uri = None
    
    with open(filepath, 'rb') as f:
        chunk_index = 0
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk: break
            
            start = chunk_index * CHUNK_SIZE
            is_final = len(chunk) < CHUNK_SIZE or (start + len(chunk) == file_size)
            command = "upload, finalize" if is_final else "upload"
            
            headers = {
                'X-Goog-Upload-Command': command,
                'X-Goog-Upload-Offset': str(start),
                'Origin': 'http://localhost'
            }
            
            resp = requests.post(upload_url, headers=headers, data=chunk)
            print(f"Flask Test Client -> Chunk {chunk_index+1} status: {resp.status_code}")
            
            if is_final:
                gemini_file_uri = resp.json().get('file', {}).get('uri')
            chunk_index += 1
            
    return gemini_file_uri

def test_flow():
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.test_client() as client:
        # Mock login by setting the user ID directly in the session
        # User ID 1 is the default USER in the CSV
        print("1. Logging in via Flask session...")
        with client.session_transaction() as sess:
            sess['_user_id'] = '1'  # Flask-Login stores user ID as string

        print("2. Getting Gemini Upload URL...")
        filepath = os.path.join('docs', 'DINANATH MONDAL - OD CLAIM.pdf')
        file_size = os.path.getsize(filepath)
        resp = client.post('/get_gemini_upload_url', json={
            "filename": "DINANATH MONDAL - OD CLAIM.pdf",
            "mime_type": "application/pdf",
            "size": file_size
        })
        
        if resp.status_code != 200:
            print(f"Failed to get URL: {resp.status_code} - {resp.data}")
            return
            
        data = json.loads(resp.data)
        upload_url = data.get('url')
        print("Got URL, uploading to Gemini...")
        
        # 3. Upload to Gemini using standard requests because it's an external API
        gemini_file_uri = upload_to_gemini(upload_url, filepath)
        
        if not gemini_file_uri:
            print("Failed to upload to Gemini.")
            return
            
        print(f"4. Processing PDF via Gemini URI: {gemini_file_uri}...")
        resp = client.post('/process_pdf', json={
            "gemini_file_uri": gemini_file_uri,
            "mime_type": "application/pdf"
        })
        
        print(f"Process Response Status: {resp.status_code}")
        if resp.status_code == 200:
            parsed = json.loads(resp.data)
            print("Successfully processed the PDF!")
            if 'raw_response' in parsed:
                print("JSON response received from Gemini.")
                print(f"Result snippet: {str(parsed)[:200]}...")
        else:
            print(f"Error processing: {resp.data}")

if __name__ == '__main__':
    test_flow()
