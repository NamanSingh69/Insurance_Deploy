from db import db
import bcrypt

db.connect()
cur = db.conn.cursor()
cur.execute("SELECT setval('users_id_seq', (SELECT COALESCE(MAX(id), 1) FROM users));")
db.conn.commit()

db.create_user({
    'username': 'NAMAN',
    'password_hash': bcrypt.hashpw(b'69420', bcrypt.gensalt()).decode()
})
print("SUCCESS: Sequence synchronized and user NAMAN created.")
