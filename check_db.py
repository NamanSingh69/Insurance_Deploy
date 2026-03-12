import sys
from db import db
db.connect()
cur = db.conn.cursor()
cur.execute("SELECT report_data_json FROM reports WHERE report_no='NIA/2026/01';")
res = cur.fetchone()
if res:
    import json
    data = res[0]
    if isinstance(data, str): data = json.loads(data)
    print("POSTGRES FIELD note_text:", data.get('assessment', {}).get('note_text', 'NULL'))
else:
    print('RECORD NOT FOUND')
