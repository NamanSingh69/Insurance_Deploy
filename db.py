import os
from dotenv import load_dotenv
load_dotenv(override=True)
import json
import uuid
from datetime import datetime, timedelta
import psycopg2
import psycopg2.pool
from psycopg2.extras import RealDictCursor

import requests
from google.oauth2.service_account import Credentials
import threading
from contextlib import contextmanager

SCOPE = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

class PostgresDB:
    def __init__(self):
        self.pool = None
        self.creds = None
        self._local_conns = threading.local()

    def connect(self):
        DATABASE_URL = os.getenv("DATABASE_URL")
        if not DATABASE_URL:
            print("Warning: DATABASE_URL not found.")
            return

        try:
            # Thread-safe connection pool: min 1 connection, max 20 connections
            self.pool = psycopg2.pool.ThreadedConnectionPool(1, 20, DATABASE_URL)
        except Exception as e:
            self.pool = None
            print(f"Warning: PostgreSQL connection pool failed: {e}")
            return

        self._run_migrations()

        # Connect Drive API
        creds_json = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
        if creds_json:
            try:
                creds_dict = json.loads(creds_json)
                self.creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPE)
            except Exception as e:
                print(f"Error initializing Google Drive credentials: {e}")

    @property
    def conn(self):
        """Return a scoped database connection from the pool."""
        try:
            from flask import has_app_context, g
            in_flask = has_app_context()
        except ImportError:
            in_flask = False

        if in_flask:
            if 'db_conn' not in g or g.db_conn is None or getattr(g.db_conn, 'closed', 0) != 0:
                if not self.pool:
                    self.connect()
                if self.pool:
                    g.db_conn = self.pool.getconn()
                    g.db_conn.autocommit = True
                else:
                    return None
            return g.db_conn

        # Outside Flask (e.g. worker thread or CLI script)
        if not hasattr(self._local_conns, 'conn') or self._local_conns.conn is None or getattr(self._local_conns.conn, 'closed', 0) != 0:
            if not self.pool:
                self.connect()
            if self.pool:
                self._local_conns.conn = self.pool.getconn()
                self._local_conns.conn.autocommit = True
            else:
                return None
        return self._local_conns.conn

    def close_scoped_connection(self):
        """Return the scoped connection back to the pool."""
        try:
            from flask import has_app_context, g
            in_flask = has_app_context()
        except ImportError:
            in_flask = False

        if in_flask:
            conn = g.pop('db_conn', None)
            if conn and self.pool:
                try:
                    if getattr(conn, 'closed', 0) != 0:
                        self.pool.putconn(conn, close=True)
                    else:
                        self.pool.putconn(conn)
                except Exception:
                    pass
            return

        conn = getattr(self._local_conns, 'conn', None)
        if conn:
            self._local_conns.conn = None
            if self.pool:
                try:
                    if getattr(conn, 'closed', 0) != 0:
                        self.pool.putconn(conn, close=True)
                    else:
                        self.pool.putconn(conn)
                except Exception:
                    pass

    def _run_migrations(self):
        """Execute numbered SQL migrations in numerical order."""
        if not self.pool:
            return
        
        conn = self.pool.getconn()
        try:
            conn.autocommit = False
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        version INTEGER PRIMARY KEY,
                        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
            conn.commit()

            migrations_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'migrations')
            if not os.path.exists(migrations_dir):
                return

            migration_files = []
            for f in os.listdir(migrations_dir):
                if f.endswith('.sql'):
                    parts = f.split('_', 1)
                    if len(parts) == 2 and parts[0].isdigit():
                        version = int(parts[0])
                        migration_files.append((version, f))

            migration_files.sort()

            for version, filename in migration_files:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1 FROM schema_migrations WHERE version = %s;", (version,))
                    if cur.fetchone():
                        continue

                print(f"Applying migration {filename} (version {version})...")
                filepath = os.path.join(migrations_dir, filename)
                with open(filepath, 'r', encoding='utf-8') as file:
                    sql_content = file.read()

                try:
                    with conn.cursor() as cur:
                        cur.execute(sql_content)
                        cur.execute("INSERT INTO schema_migrations (version) VALUES (%s);", (version,))
                    conn.commit()
                    print(f"Migration {filename} applied successfully.")
                except Exception as e:
                    conn.rollback()
                    print(f"Error applying migration {filename}: {e}")
                    raise e
        finally:
            conn.autocommit = True
            self.pool.putconn(conn)

    def _init_db(self):
        """No-op for backward compatibility."""
        pass

    def get_user_by_username(self, username):
        if not username:
            return None
        if not self.conn: self.connect()
        if not self.conn: return None # Still none after trying
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM users WHERE LOWER(TRIM(username)) = LOWER(TRIM(%s));", (username.strip(),))
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
                        address_line_2, address_line_3, contact_no, email, gemini_api_key, gemini_model
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;
                """, (
                    user_data.get('username'), user_data.get('password_hash'),
                    user_data.get('full_name'), user_data.get('qualifications'),
                    user_data.get('designation'), user_data.get('license_no'),
                    user_data.get('expiry_date'), user_data.get('membership_no'),
                    user_data.get('address_line_1'), user_data.get('address_line_2'),
                    user_data.get('address_line_3'), user_data.get('contact_no'),
                    user_data.get('email'), user_data.get('gemini_api_key'), user_data.get('gemini_model')
                ))
                return cur.fetchone()[0]
        except Exception as e:
             print(f"Error creating user: {e}")
             return None

    def update_user(self, user_id, user_data):
        if not self.conn: self.connect()
        if not self.conn: return False
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    UPDATE users SET
                        full_name = %s, qualifications = %s, designation = %s,
                        license_no = %s, expiry_date = %s, membership_no = %s,
                        address_line_1 = %s, address_line_2 = %s, address_line_3 = %s,
                        contact_no = %s, email = %s, gemini_api_key = %s, gemini_model = %s
                    WHERE id = %s;
                """, (
                    user_data.get('full_name'), user_data.get('qualifications'),
                    user_data.get('designation'), user_data.get('license_no'),
                    user_data.get('expiry_date'), user_data.get('membership_no'),
                    user_data.get('address_line_1'), user_data.get('address_line_2'),
                    user_data.get('address_line_3'), user_data.get('contact_no'),
                    user_data.get('email'), user_data.get('gemini_api_key'), user_data.get('gemini_model'),
                    user_id
                 ))
                return True
        except Exception as e:
             print(f"Error updating user profile: {e}")
             return False

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

    def get_report_by_id(self, report_id, user_id):
        """Fetches a single report by ID."""
        if not self.conn: self.connect()
        if not self.conn: return None
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM reports WHERE id = %s AND user_id = %s;", (report_id, user_id))
                row = cur.fetchone()
                if row:
                     row_dict = dict(row)
                     row_dict['id'] = str(row_dict['id'])
                     row_dict['saved_at'] = str(row_dict['saved_at']) if row_dict['saved_at'] else ''
                     if isinstance(row_dict['report_data_json'], dict):
                          row_dict['report_data_json'] = json.dumps(row_dict['report_data_json'])
                     return row_dict
            return None
        except Exception as e:
             print(f"Error getting report by ID: {e}")
             return None

    def get_last_surveyor_details(self, user_id):
        """Fetches the surveyor_details from the user's most recently saved report."""
        if not self.conn: self.connect()
        if not self.conn: return None
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT report_data_json 
                    FROM reports 
                    WHERE user_id = %s 
                    ORDER BY saved_at DESC 
                    LIMIT 1;
                """, (user_id,))
                row = cur.fetchone()
                if row:
                    data = row['report_data_json']
                    if isinstance(data, str):
                        data = json.loads(data)
                    if data:
                        return data.get('assessment', {}).get('page3_details', {}).get('surveyor_details')
            return None
        except Exception as e:
            print(f"Error getting last surveyor details: {e}")
            return None


    # --- Asset Methods ---
    def create_asset(self, user_id, storage_kind, storage_locator, filename='', mime_type='', expires_at=None, report_id=None):
        """Create an application-owned reference to a private stored file."""
        if not self.conn:
            self.connect()
        if not self.conn:
            return None
        asset_id = str(uuid.uuid4())
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    INSERT INTO assets (
                        id, user_id, storage_kind, storage_locator, filename,
                        mime_type, expires_at, report_id
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *;
                """, (asset_id, user_id, storage_kind, storage_locator, filename, mime_type, expires_at, report_id))
                return dict(cur.fetchone())
        except Exception as e:
            print(f"Error creating asset: {e}")
            return None

    def get_asset_for_user(self, asset_id, user_id):
        """Return an asset only when the requesting user owns it and it has not expired."""
        if not self.conn:
            self.connect()
        if not self.conn:
            return None
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM assets
                    WHERE id = %s
                      AND user_id = %s
                      AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP);
                """, (asset_id, user_id))
                row = cur.fetchone()
                return dict(row) if row else None
        except Exception as e:
            print(f"Error fetching asset: {e}")
            return None

    def delete_expired_assets(self):
        """Return storage records that a cleanup worker must remove from their provider."""
        if not self.conn:
            self.connect()
        if not self.conn:
            return []
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    DELETE FROM assets
                    WHERE expires_at IS NOT NULL AND expires_at <= CURRENT_TIMESTAMP
                    RETURNING *;
                """)
                return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            print(f"Error deleting expired assets: {e}")
            return []

    def migrate_legacy_photo_references(self):
        """Replace Report photo URLs with owned asset URLs without changing report content otherwise."""
        if not self.conn:
            self.connect()
        if not self.conn:
            return 0
        migrated_reports = 0
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT id, user_id, report_data_json FROM reports;")
                reports = cur.fetchall()
                for report in reports:
                    payload = report['report_data_json']
                    if isinstance(payload, str):
                        payload = json.loads(payload)
                    changed = False

                    def migrate_value(value):
                        nonlocal changed
                        if isinstance(value, dict):
                            return {key: migrate_value(item) for key, item in value.items()}
                        if isinstance(value, list):
                            return [migrate_value(item) for item in value]
                        if not isinstance(value, str):
                            return value

                        if value.startswith('/proxy_image/'):
                            storage_kind, locator = 'drive', value.removeprefix('/proxy_image/')
                        elif value.startswith('/local_image/'):
                            storage_kind, locator = 'legacy_local', value.removeprefix('/local_image/')
                        else:
                            return value

                        cur.execute("""
                            SELECT id FROM assets
                            WHERE user_id = %s AND storage_kind = %s AND storage_locator = %s
                            LIMIT 1;
                        """, (report['user_id'], storage_kind, locator))
                        existing = cur.fetchone()
                        if existing:
                            asset_id = str(existing['id'])
                        else:
                            asset_id = str(uuid.uuid4())
                            cur.execute("""
                                INSERT INTO assets (id, user_id, storage_kind, storage_locator, filename, report_id)
                                VALUES (%s, %s, %s, %s, %s, %s);
                            """, (asset_id, report['user_id'], storage_kind, locator, locator, report['id']))
                        changed = True
                        return f'/assets/{asset_id}/content'

                    migrated = migrate_value(payload)
                    if changed:
                        cur.execute("UPDATE reports SET report_data_json = %s::jsonb WHERE id = %s;", (json.dumps(migrated), report['id']))
                        migrated_reports += 1
            return migrated_reports
        except Exception as e:
            print(f"Error migrating legacy photo references: {e}")
            return 0

    def create_upload_session(self, user_id, provider, filename, mime_type, expected_size, ttl_minutes=30):
        if not self.conn: self.connect()
        if not self.conn: return None
        upload_id = str(uuid.uuid4())
        expires_at = datetime.utcnow() + timedelta(minutes=ttl_minutes)
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    INSERT INTO upload_sessions (
                        id, user_id, provider, filename, mime_type, expected_size, expires_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING *;
                """, (upload_id, user_id, provider, filename, mime_type, expected_size, expires_at))
                return dict(cur.fetchone())
        except Exception as e:
            print(f"Error creating upload session: {e}")
            return None

    def get_upload_session_for_user(self, upload_id, user_id, provider='gemini'):
        if not self.conn: self.connect()
        if not self.conn: return None
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM upload_sessions
                    WHERE id = %s AND user_id = %s AND provider = %s AND expires_at > CURRENT_TIMESTAMP;
                """, (upload_id, user_id, provider))
                row = cur.fetchone()
                return dict(row) if row else None
        except Exception as e:
            print(f"Error fetching upload session: {e}")
            return None

    def set_upload_session_uri(self, upload_id, user_id, provider_uri):
        if not self.conn: self.connect()
        if not self.conn: return False
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    UPDATE upload_sessions
                    SET provider_uri = %s
                    WHERE id = %s AND user_id = %s AND expires_at > CURRENT_TIMESTAMP;
                """, (provider_uri, upload_id, user_id))
                return cur.rowcount == 1
        except Exception as e:
            print(f"Error setting upload session URI: {e}")
            return False

    def create_job(self, user_id, kind, input_data=None):
        if not self.conn: self.connect()
        if not self.conn: return None
        job_id = str(uuid.uuid4())
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    INSERT INTO jobs (id, user_id, kind, status, input_json)
                    VALUES (%s, %s, %s, 'queued', %s::jsonb)
                    RETURNING *;
                """, (job_id, user_id, kind, json.dumps(input_data) if input_data is not None else '{}'))
                return dict(cur.fetchone())
        except Exception as e:
            print(f"Error creating job: {e}")
            return None

    def get_job_for_user(self, job_id, user_id):
        if not self.conn: self.connect()
        if not self.conn: return None
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM jobs WHERE id = %s AND user_id = %s;", (job_id, user_id))
                row = cur.fetchone()
                return dict(row) if row else None
        except Exception as e:
            print(f"Error fetching job: {e}")
            return None

            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM jobs WHERE id = %s AND user_id = %s;", (job_id, user_id))
                row = cur.fetchone()
                return dict(row) if row else None
        except Exception as e:
            print(f"Error fetching job: {e}")
            return None

    def claim_next_job(self, worker_id):
        """Atomically claim one queued job. Safe for multiple worker processes."""
        if not self.conn:
            self.connect()
        if not self.conn:
            return None
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    WITH next_job AS (
                        SELECT id FROM jobs
                        WHERE status = 'queued'
                        ORDER BY created_at
                        FOR UPDATE SKIP LOCKED
                        LIMIT 1
                    )
                    UPDATE jobs
                    SET status = 'running', started_at = CURRENT_TIMESTAMP,
                        locked_at = CURRENT_TIMESTAMP, worker_id = %s,
                        attempts = attempts + 1
                    WHERE id IN (SELECT id FROM next_job)
                    RETURNING *;
                """, (worker_id,))
                row = cur.fetchone()
                return dict(row) if row else None
        except Exception as e:
            print(f"Error claiming job: {e}")
            return None

    def complete_job(self, job_id, result_data):
        return self._finish_job(job_id, 'completed', result_data=result_data)

    def fail_job(self, job_id, error_message):
        return self._finish_job(job_id, 'error', error_message=error_message)

    def requeue_job(self, job_id):
        if not self.conn:
            self.connect()
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    UPDATE jobs
                    SET status = 'queued', locked_at = NULL, worker_id = NULL
                    WHERE id = %s;
                """, (job_id,))
                return cur.rowcount == 1
        except Exception as e:
            print(f"Error requeuing job: {e}")
            return False

    def get_job_by_request_id(self, request_id):
        if not self.conn:
            self.connect()
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM jobs
                    WHERE result_json->>'request_id' = %s;
                """, (request_id,))
                row = cur.fetchone()
                return dict(row) if row else None
        except Exception as e:
            print(f"Error fetching job by request_id: {e}")
            return None

    def _finish_job(self, job_id, status, result_data=None, error_message=None):
        if not self.conn:
            self.connect()
        if not self.conn:
            return False
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    UPDATE jobs
                    SET status = %s, result_json = %s::jsonb, error_message = %s,
                        completed_at = CURRENT_TIMESTAMP, locked_at = NULL
                    WHERE id = %s;
                """, (status, json.dumps(result_data) if result_data is not None else None, error_message, job_id))
                return cur.rowcount == 1
        except Exception as e:
            print(f"Error completing job: {e}")
            return False

    def requeue_stale_jobs(self, stale_after_minutes=15):
        """Recover work left running by a restarted worker."""
        if not self.conn:
            self.connect()
        if not self.conn:
            return 0
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    UPDATE jobs
                    SET status = 'queued', locked_at = NULL, worker_id = NULL,
                        started_at = NULL
                    WHERE status = 'running'
                      AND locked_at < CURRENT_TIMESTAMP - (%s * INTERVAL '1 minute');
                """, (stale_after_minutes,))
                return cur.rowcount
        except Exception as e:
            print(f"Error recovering jobs: {e}")
            return 0

    # --- Report Query and Numbering Methods ---
    def get_user_reports_page(self, user_id, search_query='', page=1, page_size=50):
        """Search report metadata in PostgreSQL instead of filtering it in Flask."""
        if not self.conn:
            self.connect()
        if not self.conn:
            return {'items': [], 'page': page, 'page_size': page_size, 'total': 0}
        page = max(1, int(page))
        page_size = min(100, max(1, int(page_size)))
        pattern = f"%{search_query.strip()}%"
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                where_sql = """
                    user_id = %s AND (
                        %s = '' OR report_no ILIKE %s OR insured_name ILIKE %s
                        OR vehicle_no ILIKE %s OR claim_no ILIKE %s OR policy_no ILIKE %s
                    )
                """
                params = (user_id, search_query.strip(), pattern, pattern, pattern, pattern, pattern)
                cur.execute(f"SELECT COUNT(*) AS total FROM reports WHERE {where_sql};", params)
                total = int(cur.fetchone()['total'])
                cur.execute(f"""
                    SELECT id, user_id, report_no, insured_name, vehicle_no, claim_no,
                           policy_no, saved_at, include_in_consolidated
                    FROM reports WHERE {where_sql}
                    ORDER BY saved_at DESC
                    LIMIT %s OFFSET %s;
                """, params + (page_size, (page - 1) * page_size))
                items = []
                for row in cur.fetchall():
                    item = dict(row)
                    item['id'] = str(item['id'])
                    item['saved_at'] = str(item['saved_at']) if item['saved_at'] else ''
                    items.append(item)
                return {'items': items, 'page': page, 'page_size': page_size, 'total': total}
        except Exception as e:
            print(f"Error searching report metadata: {e}")
            return {'items': [], 'page': page, 'page_size': page_size, 'total': 0}

    def reserve_report_number(self, user_id, prefix, report_year):
        """Reserve a report sequence atomically; unused reservations intentionally leave gaps."""
        if not self.conn:
            self.connect()
        if not self.conn:
            return None
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    INSERT INTO report_number_counters (user_id, prefix, report_year, next_sequence)
                    VALUES (%s, %s, %s, 2)
                    ON CONFLICT (user_id, prefix, report_year)
                    DO UPDATE SET next_sequence = report_number_counters.next_sequence + 1
                    RETURNING next_sequence - 1 AS sequence;
                """, (user_id, prefix, report_year))
                return int(cur.fetchone()['sequence'])
        except Exception as e:
            print(f"Error reserving report number: {e}")
            return None


    def save_report(self, user_id, report_data_dict, existing_report_id=None):
        """Saves a report to PostgreSQL natively as JSONB!
        
        If existing_report_id is provided (the UUID of the currently-loaded report),
        we UPDATE that specific row. This prevents silent overwrites caused by two
        different reports sharing the same report_no string.
        
        If existing_report_id is None (brand-new report), we INSERT a fresh row.
        """
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
                if existing_report_id:
                    # PRIORITY: If we know which row to update (by UUID), update it directly.
                    # First verify this UUID actually belongs to this user (security check).
                    cur.execute("SELECT id FROM reports WHERE id = %s AND user_id = %s;", (existing_report_id, user_id))
                    verified = cur.fetchone()
                    if verified:
                        cur.execute("""
                            UPDATE reports SET
                                report_no = %s, insured_name = %s, vehicle_no = %s, claim_no = %s,
                                policy_no = %s, saved_at = %s, report_data_json = %s::jsonb
                            WHERE id = %s RETURNING id;
                        """, (report_no, insured_name, vehicle_no, claim_no, policy_no, saved_at, report_data_json, existing_report_id))
                        return cur.fetchone()[0]
                    else:
                        print(f"Warning: existing_report_id {existing_report_id} not found for user {user_id}. Creating new record.")
                        existing_report_id = None  # Fall through to insert

                if not existing_report_id:
                    # No existing ID provided â€” this is a new report. Insert fresh row.
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
    def get_resumable_upload_url(self, filename, mime_type='application/pdf', origin=None):
        result = self.get_resumable_upload_url_with_token(filename, mime_type, origin)
        return result['url'] if result else None
    
    def get_resumable_upload_url_with_token(self, filename, mime_type='application/pdf', origin=None):
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
            if origin:
                headers['Origin'] = origin
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
        """Upload report PDF into the service account's own Drive under 'Survey Reports' root."""
        try:
            root_folder_id = self._find_or_create_folder('Survey Reports')
            if not root_folder_id: return None

            folder_name = "".join(c for c in vehicle_no if c.isalnum() or c in ('_', '-', ' ')).strip() if vehicle_no else 'Unknown_Vehicle'
            vehicle_folder_id = self._find_or_create_folder(folder_name, root_folder_id)
            if not vehicle_folder_id: return None

            headers = self._get_auth_header()
            query = f"name='{filename}' and '{vehicle_folder_id}' in parents and trashed=false"
            search_url = "https://www.googleapis.com/drive/v3/files"
            params = {'q': query, 'fields': 'files(id,webViewLink)', 'spaces': 'drive'}

            search_response = requests.get(search_url, headers=headers, params=params)
            existing_files = []
            if search_response.status_code == 200:
                existing_files = search_response.json().get('files', [])

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
                files_multipart = {
                    'metadata': ('', json.dumps({'name': filename, 'parents': [vehicle_folder_id], 'mimeType': 'application/pdf'}), 'application/json'),
                    'file': (filename, pdf_bytes, 'application/pdf')
                }
                response = requests.post(upload_url, headers=headers, files=files_multipart)
                if response.status_code in [200, 201]:
                    return response.json().get('webViewLink', f"https://drive.google.com/file/d/{response.json().get('id')}/view")

            print(f"Drive upload failed: {response.status_code} - {response.text[:200]}")
            return None
        except Exception as e:
            print(f"Drive upload error: {e}")
            return None


db = PostgresDB()