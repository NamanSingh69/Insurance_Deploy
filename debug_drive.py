"""Test upload to service account's OWN Drive (Survey Reports folder)."""
import os
from dotenv import load_dotenv
load_dotenv(override=True)
from db import db

db.connect()
test_pdf = b'%PDF-1.4 test'
result = db.upload_report_pdf(test_pdf, 'debug_test.pdf', 'TEST123')
print("Upload result:", result)
print("SUCCESS!" if result else "FAILED - still None")
