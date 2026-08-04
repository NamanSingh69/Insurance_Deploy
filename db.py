import os
from dotenv import load_dotenv
# Tests and process-level deployment configuration must win over a developer's
# local .env file.  ``override=True`` made the test suite talk to production
# resources whenever a local .env happened to be present.
load_dotenv()
import json
import uuid
from datetime import date, datetime, timedelta
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
                    is_applied = cur.fetchone()
                conn.commit()
                if is_applied:
                    continue

                print(f"Applying migration {filename} (version {version})...")
                filepath = os.path.join(migrations_dir, filename)
                with open(filepath, 'r', encoding='utf-8') as file:
                    sql_content = file.read()

                try:
                    with conn.cursor() as cur:
                        cur.execute(sql_content)
                        cur.execute("INSERT INTO schema_migrations (version) VALUES (%s) ON CONFLICT DO NOTHING;", (version,))
                    conn.commit()
                    print(f"Migration {filename} applied successfully.")
                except Exception as e:
                    conn.rollback()
                    print(f"Warning applying migration {filename}: {e}")
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
                        address_line_2, address_line_3, contact_no, email, encrypted_gemini_api_key, gemini_model,
                        role, admin_id, is_locked, permissions, must_change_password
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;
                """, (
                    user_data.get('username'), user_data.get('password_hash'),
                    user_data.get('full_name'), user_data.get('qualifications'),
                    user_data.get('designation'), user_data.get('license_no'),
                    user_data.get('expiry_date'), user_data.get('membership_no'),
                    user_data.get('address_line_1'), user_data.get('address_line_2'),
                    user_data.get('address_line_3'), user_data.get('contact_no'),
                    user_data.get('email'), user_data.get('encrypted_gemini_api_key'), user_data.get('gemini_model'),
                    user_data.get('role', 'employee'), user_data.get('admin_id'),
                    bool(user_data.get('is_locked', False)), json.dumps(user_data.get('permissions') or {}),
                    bool(user_data.get('must_change_password', False))
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
                        contact_no = %s, email = %s, gemini_model = %s
                    WHERE id = %s;
                """, (
                    user_data.get('full_name'), user_data.get('qualifications'),
                    user_data.get('designation'), user_data.get('license_no'),
                    user_data.get('expiry_date'), user_data.get('membership_no'),
                    user_data.get('address_line_1'), user_data.get('address_line_2'),
                    user_data.get('address_line_3'), user_data.get('contact_no'),
                    user_data.get('email'), user_data.get('gemini_model'),
                    user_id
                 ))
                return True
        except Exception as e:
             print(f"Error updating user profile: {e}")
             return False

    def set_user_gemini_api_key(self, user_id, encrypted_value):
        """Persist an encrypted user key and erase the legacy plaintext column."""
        if not self.conn:
            self.connect()
        if not self.conn:
            return False
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    UPDATE users
                    SET encrypted_gemini_api_key = %s, gemini_api_key = NULL
                    WHERE id = %s;
                """, (encrypted_value, user_id))
                return cur.rowcount == 1
        except Exception as e:
            print(f"Error storing encrypted Gemini credential: {e}")
            return False

    def clear_user_gemini_api_key(self, user_id):
        if not self.conn:
            self.connect()
        if not self.conn:
            return False
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    UPDATE users
                    SET encrypted_gemini_api_key = NULL, gemini_api_key = NULL
                    WHERE id = %s;
                """, (user_id,))
                return cur.rowcount == 1
        except Exception as e:
            print(f"Error clearing Gemini credential: {e}")
            return False

    def get_users_with_legacy_gemini_keys(self):
        """Return only rows requiring the one-time plaintext credential migration."""
        if not self.conn:
            self.connect()
        if not self.conn:
            return []
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT id, gemini_api_key
                    FROM users
                    WHERE gemini_api_key IS NOT NULL AND gemini_api_key <> ''
                      AND (encrypted_gemini_api_key IS NULL OR encrypted_gemini_api_key = '');
                """)
                return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            print(f"Error reading legacy Gemini credentials: {e}")
            return []

    def get_users_without_signature_asset(self):
        if not self.conn:
            self.connect()
        if not self.conn:
            return []
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT id FROM users WHERE signature_asset_id IS NULL;")
                return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            print(f"Error reading users without signature assets: {e}")
            return []

    def set_user_signature_asset(self, user_id, asset_id):
        if not self.conn:
            self.connect()
        if not self.conn:
            return False
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    UPDATE users SET signature_asset_id = %s WHERE id = %s;
                """, (asset_id, user_id))
                return cur.rowcount == 1
        except Exception as e:
            print(f"Error storing signature asset: {e}")
            return False

    # --- Workspace User Management ---
    def get_workspace_id_for_user(self, user_id):
        user = self.get_user_by_id(user_id)
        if not user:
            return None
        if user.get('role') == 'admin':
            return user.get('id')
        return user.get('admin_id')

    def list_admin_users(self, admin_id):
        if not self.conn: self.connect()
        if not self.conn: return []
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT id, username, full_name, email, role, is_locked, permissions,
                           must_change_password, admin_id
                    FROM users
                    WHERE admin_id = %s AND role = 'employee'
                    ORDER BY username ASC;
                """, (admin_id,))
                return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            print(f"Error listing admin users: {e}")
            return []

    def get_admin_user(self, admin_id, user_id):
        if not self.conn: self.connect()
        if not self.conn: return None
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM users WHERE id = %s AND admin_id = %s AND role = 'employee';", (user_id, admin_id))
                return cur.fetchone()
        except Exception as e:
            print(f"Error fetching managed user: {e}")
            return None

    def set_user_locked(self, admin_id, user_id, is_locked):
        if not self.conn: self.connect()
        if not self.conn: return False
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    UPDATE users SET is_locked = %s
                    WHERE id = %s AND admin_id = %s AND role = 'employee'
                    RETURNING id;
                """, (bool(is_locked), user_id, admin_id))
                return cur.fetchone() is not None
        except Exception as e:
            print(f"Error locking user: {e}")
            return False

    def reset_user_password(self, admin_id, user_id, password_hash):
        if not self.conn: self.connect()
        if not self.conn: return False
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    UPDATE users SET password_hash = %s, must_change_password = TRUE
                    WHERE id = %s AND admin_id = %s AND role = 'employee'
                    RETURNING id;
                """, (password_hash, user_id, admin_id))
                return cur.fetchone() is not None
        except Exception as e:
            print(f"Error resetting password: {e}")
            return False

    def update_user_permissions(self, admin_id, user_id, permissions):
        if not self.conn: self.connect()
        if not self.conn: return False
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    UPDATE users SET permissions = %s::jsonb
                    WHERE id = %s AND admin_id = %s AND role = 'employee'
                    RETURNING id;
                """, (json.dumps(permissions or {}), user_id, admin_id))
                return cur.fetchone() is not None
        except Exception as e:
            print(f"Error updating permissions: {e}")
            return False

    def change_user_password(self, user_id, password_hash):
        if not self.conn: self.connect()
        if not self.conn: return False
        try:
            with self.conn.cursor() as cur:
                cur.execute("UPDATE users SET password_hash = %s, must_change_password = FALSE WHERE id = %s RETURNING id;", (password_hash, user_id))
                return cur.fetchone() is not None
        except Exception as e:
            print(f"Error changing password: {e}")
            return False

    def promote_user_to_admin(self, username):
        if not self.conn: self.connect()
        if not self.conn: return False
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    UPDATE users SET role = 'admin', admin_id = NULL, is_locked = FALSE
                    WHERE LOWER(TRIM(username)) = LOWER(TRIM(%s))
                    RETURNING id;
                """, (username,))
                return cur.fetchone() is not None
        except Exception as e:
            print(f"Error promoting admin: {e}")
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
    def create_asset(self, user_id, storage_kind, storage_locator, filename='', mime_type='',
                     expires_at=None, report_id=None, purpose='generic', size_bytes=None,
                     checksum_sha256=None):
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
                        mime_type, expires_at, report_id, purpose, size_bytes, checksum_sha256
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *;
                """, (
                    asset_id, user_id, storage_kind, storage_locator, filename, mime_type, expires_at, report_id,
                    purpose, size_bytes, checksum_sha256
                ))
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

    def get_asset_for_access(self, asset_id, user_id, workspace_admin_id=None):
        """Return an unexpired asset visible to the caller's personal or shared workspace."""
        if not self.conn:
            self.connect()
        if not self.conn:
            return None
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT a.*
                    FROM assets AS a
                    LEFT JOIN reports AS r ON r.id = a.report_id
                    WHERE a.id = %s
                      AND (a.expires_at IS NULL OR a.expires_at > CURRENT_TIMESTAMP)
                      AND (
                          a.user_id = %s
                          OR (r.workspace_admin_id IS NULL AND r.user_id = %s)
                          OR (%s IS NOT NULL AND r.workspace_admin_id = %s)
                      );
                """, (asset_id, user_id, user_id, workspace_admin_id, workspace_admin_id))
                row = cur.fetchone()
                return dict(row) if row else None
        except Exception as e:
            print(f"Error fetching accessible asset: {e}")
            return None

    def attach_assets_to_report(self, asset_ids, report_id, user_id):
        """Attach newly uploaded assets to their report and make them durable."""
        clean_ids = [str(asset_id) for asset_id in (asset_ids or []) if asset_id]
        if not clean_ids:
            return True
        if not self.conn:
            self.connect()
        if not self.conn:
            return False
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    UPDATE assets
                    SET report_id = %s, expires_at = NULL
                    WHERE id = ANY(%s) AND user_id = %s;
                """, (report_id, clean_ids, user_id))
                return cur.rowcount == len(clean_ids)
        except Exception as e:
            print(f"Error attaching assets to report: {e}")
            return False

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

    # --- Shared Claim Register / Workspace Report Methods ---
    def _report_row_to_dict(self, row):
        item = dict(row)
        item['id'] = str(item.get('id'))
        for key in ('saved_at', 'updated_at', 'email_received_date'):
            if item.get(key) is not None:
                item[key] = item[key].isoformat() if isinstance(item[key], datetime) else str(item[key])
        if isinstance(item.get('report_data_json'), dict):
            item['report_data_json'] = json.dumps(item['report_data_json'])
        return item

    def get_workspace_reports_page(self, workspace_admin_id, search_query='', page=1, page_size=50,
                                   status=None, month=None, insurer=None):
        """Return only records created in an admin-owned shared workspace."""
        if not self.conn: self.connect()
        if not self.conn:
            return {'items': [], 'page': page, 'page_size': page_size, 'total': 0}
        page = max(1, int(page))
        page_size = min(100, max(1, int(page_size)))
        pattern = f"%{(search_query or '').strip()}%"
        filters = ["workspace_admin_id = %s", "(%s = '' OR report_no ILIKE %s OR insured_name ILIKE %s OR vehicle_no ILIKE %s OR claim_no ILIKE %s OR policy_no ILIKE %s)"]
        params = [workspace_admin_id, (search_query or '').strip(), pattern, pattern, pattern, pattern, pattern]
        if status:
            filters.append("status = %s")
            params.append(status)
        if month:
            filters.append("TO_CHAR(COALESCE(email_received_date, saved_at), 'YYYY-MM') = %s")
            params.append(month)
        if insurer:
            filters.append("COALESCE(report_data_json->'survey_report'->>'insurer', '') ILIKE %s")
            params.append(f"%{insurer.strip()}%")
        where_sql = ' AND '.join(filters)
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(f"SELECT COUNT(*) AS total FROM reports WHERE {where_sql};", tuple(params))
                total = int(cur.fetchone()['total'])
                cur.execute(f"""
                    SELECT id, user_id, workspace_admin_id, report_no, insured_name, vehicle_no, claim_no,
                           policy_no, saved_at, updated_at, status, survey_type, email_received_date,
                           COALESCE(report_data_json->'survey_report'->>'insurer', '') AS insurer
                    FROM reports WHERE {where_sql}
                    ORDER BY COALESCE(email_received_date, saved_at) DESC
                    LIMIT %s OFFSET %s;
                """, tuple(params + [page_size, (page - 1) * page_size]))
                return {
                    'items': [self._report_row_to_dict(row) for row in cur.fetchall()],
                    'page': page,
                    'page_size': page_size,
                    'total': total,
                }
        except Exception as e:
            print(f"Error fetching workspace reports: {e}")
            return {'items': [], 'page': page, 'page_size': page_size, 'total': 0}

    def get_accessible_reports_page(self, workspace_admin_id, user_id, search_query='', page=1, page_size=50):
        """Return shared workspace records plus legacy records owned by this user only."""
        if not self.conn:
            self.connect()
        if not self.conn:
            return {'items': [], 'page': page, 'page_size': page_size, 'total': 0}
        page = max(1, int(page))
        page_size = min(100, max(1, int(page_size)))
        pattern = f"%{(search_query or '').strip()}%"
        if workspace_admin_id:
            ownership_sql = "(workspace_admin_id = %s OR (workspace_admin_id IS NULL AND user_id = %s))"
            params = [workspace_admin_id, user_id]
        else:
            ownership_sql = "workspace_admin_id IS NULL AND user_id = %s"
            params = [user_id]
        filters = [
            ownership_sql,
            "(%s = '' OR report_no ILIKE %s OR insured_name ILIKE %s OR vehicle_no ILIKE %s OR claim_no ILIKE %s OR policy_no ILIKE %s)",
        ]
        params.extend([(search_query or '').strip(), pattern, pattern, pattern, pattern, pattern])
        where_sql = ' AND '.join(filters)
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(f"SELECT COUNT(*) AS total FROM reports WHERE {where_sql};", tuple(params))
                total = int(cur.fetchone()['total'])
                cur.execute(f"""
                    SELECT id, user_id, workspace_admin_id, report_no, insured_name, vehicle_no, claim_no,
                           policy_no, saved_at, updated_at, status, survey_type, email_received_date,
                           workspace_admin_id IS NULL AS is_legacy
                    FROM reports WHERE {where_sql}
                    ORDER BY COALESCE(email_received_date, saved_at) DESC
                    LIMIT %s OFFSET %s;
                """, tuple(params + [page_size, (page - 1) * page_size]))
                return {
                    'items': [self._report_row_to_dict(row) for row in cur.fetchall()],
                    'page': page,
                    'page_size': page_size,
                    'total': total,
                }
        except Exception as e:
            print(f"Error fetching accessible reports: {e}")
            return {'items': [], 'page': page, 'page_size': page_size, 'total': 0}

    def get_accessible_report_by_id(self, report_id, workspace_admin_id, user_id):
        """Fetch a shared record or an unshared legacy record owned by this user."""
        if not self.conn:
            self.connect()
        if not self.conn:
            return None
        params = [report_id]
        if workspace_admin_id:
            ownership_sql = "(workspace_admin_id = %s OR (workspace_admin_id IS NULL AND user_id = %s))"
            params.extend([workspace_admin_id, user_id])
        else:
            ownership_sql = "workspace_admin_id IS NULL AND user_id = %s"
            params.append(user_id)
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(f"SELECT * FROM reports WHERE id = %s AND {ownership_sql};", tuple(params))
                row = cur.fetchone()
                return self._report_row_to_dict(row) if row else None
        except Exception as e:
            print(f"Error fetching accessible report: {e}")
            return None

    def get_workspace_report_by_id(self, report_id, workspace_admin_id):
        if not self.conn: self.connect()
        if not self.conn: return None
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM reports WHERE id = %s AND workspace_admin_id = %s;", (report_id, workspace_admin_id))
                row = cur.fetchone()
                return self._report_row_to_dict(row) if row else None
        except Exception as e:
            print(f"Error fetching workspace report: {e}")
            return None

    def find_workspace_report_by_claim_no(self, workspace_admin_id, claim_no):
        if not claim_no:
            return None
        if not self.conn: self.connect()
        if not self.conn: return None
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM reports
                    WHERE workspace_admin_id = %s AND LOWER(TRIM(claim_no)) = LOWER(TRIM(%s))
                    ORDER BY saved_at DESC LIMIT 1;
                """, (workspace_admin_id, claim_no))
                row = cur.fetchone()
                return self._report_row_to_dict(row) if row else None
        except Exception as e:
            print(f"Error finding claim report: {e}")
            return None

    def save_workspace_report(self, user_id, workspace_admin_id, report_data_dict, existing_report_id=None,
                              status='new_appointment', survey_type='final', gmail_message_id=None,
                              email_received_date=None):
        """Save a shared operational report while keeping its author and workspace distinct."""
        if not self.conn: self.connect()
        if not self.conn: return None
        survey = report_data_dict.get('survey_report', {}) or {}
        report_no = str(survey.get('report_no', '')).strip()
        insured_name = str(survey.get('insured', '')).strip()
        vehicle_no = str(survey.get('vehicle_regn_no', '')).strip()
        claim_no = str(survey.get('claim_no', '')).strip()
        policy_no = str(survey.get('policy_no', '')).strip()
        now = datetime.utcnow()
        payload = json.dumps(report_data_dict)
        try:
            with self.conn.cursor() as cur:
                if existing_report_id:
                    cur.execute("SELECT id FROM reports WHERE id = %s AND workspace_admin_id = %s;", (existing_report_id, workspace_admin_id))
                    if cur.fetchone():
                        cur.execute("""
                            UPDATE reports SET report_no = %s, insured_name = %s, vehicle_no = %s,
                                claim_no = %s, policy_no = %s, saved_at = %s, updated_at = %s,
                                updated_by = %s, status = %s, survey_type = %s,
                                report_data_json = %s::jsonb
                            WHERE id = %s RETURNING id;
                        """, (report_no, insured_name, vehicle_no, claim_no, policy_no, now, now,
                              user_id, status, survey_type, payload, existing_report_id))
                        return cur.fetchone()[0]

                report_id = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO reports (
                        id, user_id, workspace_admin_id, report_no, insured_name, vehicle_no,
                        claim_no, policy_no, saved_at, updated_at, updated_by, status, survey_type,
                        gmail_message_id, email_received_date, include_in_consolidated, report_data_json
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE, %s::jsonb)
                    RETURNING id;
                """, (report_id, user_id, workspace_admin_id, report_no, insured_name, vehicle_no,
                      claim_no, policy_no, now, now, user_id, status, survey_type,
                      gmail_message_id, email_received_date, payload))
                return cur.fetchone()[0]
        except Exception as e:
            print(f"Error saving workspace report: {e}")
            return None

    def update_workspace_report_status(self, report_id, workspace_admin_id, user_id, status):
        if not self.conn: self.connect()
        if not self.conn: return False
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    UPDATE reports SET status = %s, updated_by = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s AND workspace_admin_id = %s RETURNING id;
                """, (status, user_id, report_id, workspace_admin_id))
                return cur.fetchone() is not None
        except Exception as e:
            print(f"Error updating report status: {e}")
            return False

    def delete_workspace_report(self, report_id, workspace_admin_id):
        if not self.conn: self.connect()
        if not self.conn: return False
        try:
            with self.conn.cursor() as cur:
                cur.execute("DELETE FROM reports WHERE id = %s AND workspace_admin_id = %s RETURNING id;", (report_id, workspace_admin_id))
                return cur.fetchone() is not None
        except Exception as e:
            print(f"Error deleting workspace report: {e}")
            return False

    def delete_accessible_report(self, report_id, workspace_admin_id, user_id):
        """Delete a shared report or only the requesting user's legacy report."""
        if not self.conn:
            self.connect()
        if not self.conn:
            return False
        params = [report_id]
        if workspace_admin_id:
            ownership_sql = "(workspace_admin_id = %s OR (workspace_admin_id IS NULL AND user_id = %s))"
            params.extend([workspace_admin_id, user_id])
        else:
            ownership_sql = "workspace_admin_id IS NULL AND user_id = %s"
            params.append(user_id)
        try:
            with self.conn.cursor() as cur:
                cur.execute(f"DELETE FROM reports WHERE id = %s AND {ownership_sql} RETURNING id;", tuple(params))
                return cur.fetchone() is not None
        except Exception as e:
            print(f"Error deleting accessible report: {e}")
            return False

    def get_workspace_dashboard(self, workspace_admin_id, date_range=None):
        """Return operational counters and financial aggregates for a workspace with optional date range filter."""
        default = {'total_claims': 0, 'pending_claims': 0, 'completed_claims': 0,
                   'new_appointment': 0, 'inspection_pending': 0, 'documents_awaited': 0,
                   'report_under_preparation': 0, 'report_submitted': 0, 'closed': 0,
                   'total_invoiced': 0.0, 'amount_received': 0.0, 'outstanding_fees': 0.0,
                   'overdue_count': 0}
        if not self.conn: self.connect()
        if not self.conn: return default

        days_map = {'1m': 30, '3m': 90, '1y': 365}
        days = days_map.get(date_range)
        cutoff = (datetime.now() - timedelta(days=days)).isoformat() if days else None

        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                if cutoff:
                    cur.execute("""
                        SELECT status, COUNT(*) AS count FROM reports
                        WHERE workspace_admin_id = %s AND saved_at >= %s GROUP BY status;
                    """, (workspace_admin_id, cutoff))
                else:
                    cur.execute("""
                        SELECT status, COUNT(*) AS count FROM reports
                        WHERE workspace_admin_id = %s GROUP BY status;
                    """, (workspace_admin_id,))
                for row in cur.fetchall():
                    default[row['status']] = int(row['count'])
                    default['total_claims'] += int(row['count'])
                default['completed_claims'] = default['report_submitted'] + default['closed']
                default['pending_claims'] = default['total_claims'] - default['completed_claims']

                if cutoff:
                    cutoff_date = (datetime.now() - timedelta(days=days)).date()
                    cur.execute("""
                        SELECT COALESCE(SUM(gross_invoice_value), 0) AS total_invoiced,
                               COALESCE(SUM(amount_received), 0) AS amount_received,
                               COALESCE(SUM(outstanding_amount), 0) AS outstanding_fees,
                               COUNT(*) FILTER (WHERE due_date < CURRENT_DATE AND outstanding_amount > 0) AS overdue_count
                        FROM fee_bills WHERE workspace_admin_id = %s AND invoice_date >= %s;
                    """, (workspace_admin_id, cutoff_date))
                else:
                    cur.execute("""
                        SELECT COALESCE(SUM(gross_invoice_value), 0) AS total_invoiced,
                               COALESCE(SUM(amount_received), 0) AS amount_received,
                               COALESCE(SUM(outstanding_amount), 0) AS outstanding_fees,
                               COUNT(*) FILTER (WHERE due_date < CURRENT_DATE AND outstanding_amount > 0) AS overdue_count
                        FROM fee_bills WHERE workspace_admin_id = %s;
                    """, (workspace_admin_id,))
                fees = cur.fetchone() or {}
                for key in ('total_invoiced', 'amount_received', 'outstanding_fees'):
                    default[key] = float(fees.get(key) or 0)
                default['overdue_count'] = int(fees.get('overdue_count') or 0)
                return default
        except Exception as e:
            print(f"Error fetching dashboard: {e}")
            return default


    # --- Personal Google Drive Integration ---
    def get_drive_integration(self, user_id):
        if not self.conn:
            self.connect()
        if not self.conn:
            return None
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM drive_integrations WHERE user_id = %s;", (user_id,))
                row = cur.fetchone()
                return dict(row) if row else None
        except Exception as e:
            print(f"Error reading Drive integration: {e}")
            return None

    def save_drive_integration(self, user_id, encrypted_token, account_email=None):
        if not self.conn:
            self.connect()
        if not self.conn:
            return False
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO drive_integrations (user_id, encrypted_token, account_email)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (user_id) DO UPDATE SET
                        encrypted_token = EXCLUDED.encrypted_token,
                        account_email = COALESCE(EXCLUDED.account_email, drive_integrations.account_email),
                        updated_at = CURRENT_TIMESTAMP;
                """, (user_id, encrypted_token, account_email))
                return True
        except Exception as e:
            print(f"Error saving Drive integration: {e}")
            return False

    def delete_drive_integration(self, user_id):
        if not self.conn:
            self.connect()
        if not self.conn:
            return False
        try:
            with self.conn.cursor() as cur:
                cur.execute("DELETE FROM drive_integrations WHERE user_id = %s;", (user_id,))
                return cur.rowcount == 1
        except Exception as e:
            print(f"Error deleting Drive integration: {e}")
            return False

    # --- Gmail Workspace Integration ---
    def get_gmail_integration(self, workspace_admin_id):
        if not self.conn: self.connect()
        if not self.conn: return None
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM gmail_integrations WHERE workspace_admin_id = %s;", (workspace_admin_id,))
                row = cur.fetchone()
                return dict(row) if row else None
        except Exception as e:
            print(f"Error reading Gmail integration: {e}")
            return None

    def save_gmail_integration(self, workspace_admin_id, encrypted_token, mailbox_email=None):
        if not self.conn: self.connect()
        if not self.conn: return False
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO gmail_integrations (workspace_admin_id, encrypted_token, mailbox_email)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (workspace_admin_id) DO UPDATE SET
                        encrypted_token = EXCLUDED.encrypted_token,
                        mailbox_email = EXCLUDED.mailbox_email,
                        updated_at = CURRENT_TIMESTAMP;
                """, (workspace_admin_id, encrypted_token, mailbox_email))
                return True
        except Exception as e:
            print(f"Error saving Gmail integration: {e}")
            return False

    def delete_gmail_integration(self, workspace_admin_id):
        if not self.conn: self.connect()
        if not self.conn: return False
        try:
            with self.conn.cursor() as cur:
                cur.execute("DELETE FROM gmail_integrations WHERE workspace_admin_id = %s;", (workspace_admin_id,))
                return True
        except Exception as e:
            print(f"Error deleting Gmail integration: {e}")
            return False

    def get_gmail_sender_domains(self, workspace_admin_id):
        if not self.conn: self.connect()
        if not self.conn: return []
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT id, domain, created_at FROM gmail_sender_domains WHERE workspace_admin_id = %s ORDER BY domain;", (workspace_admin_id,))
                return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            print(f"Error reading Gmail sender domains: {e}")
            return []

    def add_gmail_sender_domain(self, workspace_admin_id, domain):
        if not self.conn: self.connect()
        if not self.conn: return None
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    INSERT INTO gmail_sender_domains (workspace_admin_id, domain)
                    VALUES (%s, LOWER(%s))
                    ON CONFLICT (workspace_admin_id, domain) DO UPDATE SET domain = EXCLUDED.domain
                    RETURNING id, domain;
                """, (workspace_admin_id, domain.strip()))
                row = cur.fetchone()
                return dict(row) if row else None
        except Exception as e:
            print(f"Error adding Gmail sender domain: {e}")
            return None

    def delete_gmail_sender_domain(self, workspace_admin_id, domain_id):
        if not self.conn: self.connect()
        if not self.conn: return False
        try:
            with self.conn.cursor() as cur:
                cur.execute("DELETE FROM gmail_sender_domains WHERE id = %s AND workspace_admin_id = %s RETURNING id;", (domain_id, workspace_admin_id))
                return cur.fetchone() is not None
        except Exception as e:
            print(f"Error deleting Gmail sender domain: {e}")
            return False

    def get_gmail_sync_message(self, gmail_message_id):
        if not self.conn: self.connect()
        if not self.conn: return None
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM gmail_sync_messages WHERE gmail_message_id = %s;", (gmail_message_id,))
                row = cur.fetchone()
                return dict(row) if row else None
        except Exception as e:
            print(f"Error reading Gmail sync message: {e}")
            return None

    def record_gmail_sync_message(self, gmail_message_id, workspace_admin_id, report_id=None,
                                  sender_email=None, subject=None, received_at=None,
                                  parse_data=None, sync_status='processed', error_message=None):
        if not self.conn: self.connect()
        if not self.conn: return False
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO gmail_sync_messages (
                        gmail_message_id, workspace_admin_id, report_id, sender_email, subject,
                        received_at, parse_data_json, sync_status, error_message
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s)
                    ON CONFLICT (gmail_message_id) DO UPDATE SET
                        report_id = EXCLUDED.report_id,
                        parse_data_json = EXCLUDED.parse_data_json,
                        sync_status = EXCLUDED.sync_status,
                        error_message = EXCLUDED.error_message,
                        processed_at = CURRENT_TIMESTAMP;
                """, (gmail_message_id, workspace_admin_id, report_id, sender_email, subject,
                      received_at, json.dumps(parse_data or {}), sync_status, error_message))
                return True
        except Exception as e:
            print(f"Error recording Gmail sync message: {e}")
            return False

    def cancel_gmail_sync_message(self, gmail_message_id):
        if not self.conn: self.connect()
        if not self.conn: return False
        try:
            with self.conn.cursor() as cur:
                cur.execute("UPDATE gmail_sync_messages SET sync_status = 'cancelled' WHERE gmail_message_id = %s;", (gmail_message_id,))
                return True
        except Exception as e:
            print(f"Error cancelling Gmail sync message: {e}")
            return False

    def get_pending_gmail_messages(self, workspace_admin_id):
        if not self.conn: self.connect()
        if not self.conn: return []
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM gmail_sync_messages
                    WHERE workspace_admin_id = %s AND sync_status NOT IN ('processed', 'cancelled')
                    ORDER BY processed_at DESC;
                """, (workspace_admin_id,))
                return [dict(r) for r in cur.fetchall()]
        except Exception as e:
            print(f"Error fetching pending Gmail messages: {e}")
            return []

    def get_claim_reminder(self, report_id):
        if not self.conn: self.connect()
        if not self.conn: return None
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM claim_reminders WHERE report_id = %s;", (report_id,))
                row = cur.fetchone()
                return dict(row) if row else None
        except Exception as e:
            print(f"Error fetching claim reminder: {e}")
            return None

    def update_claim_reminder(self, report_id, workspace_admin_id, claim_no, reminder_count, claim_manager_email=None, claim_manager_phone=None):
        if not self.conn: self.connect()
        if not self.conn: return False
        try:
            now = datetime.now()
            next_due = now + timedelta(days=7) if reminder_count < 3 else None
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO claim_reminders (
                        report_id, workspace_admin_id, claim_no, reminder_count, last_sent_at, next_due_at,
                        claim_manager_email, claim_manager_phone, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (report_id) DO UPDATE SET
                        reminder_count = EXCLUDED.reminder_count,
                        last_sent_at = EXCLUDED.last_sent_at,
                        next_due_at = EXCLUDED.next_due_at,
                        claim_manager_email = COALESCE(EXCLUDED.claim_manager_email, claim_reminders.claim_manager_email),
                        claim_manager_phone = COALESCE(EXCLUDED.claim_manager_phone, claim_reminders.claim_manager_phone),
                        updated_at = EXCLUDED.updated_at;
                """, (report_id, workspace_admin_id, claim_no, reminder_count, now, next_due,
                      claim_manager_email, claim_manager_phone, now))
                return True
        except Exception as e:
            print(f"Error updating claim reminder: {e}")
            return False

    def get_due_reminders(self):
        if not self.conn: self.connect()
        if not self.conn: return []
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT r.*, cr.reminder_count, cr.claim_manager_email, cr.claim_manager_phone
                    FROM reports r
                    JOIN claim_reminders cr ON r.id = cr.report_id
                    WHERE r.status = 'documents_awaited'
                      AND cr.reminder_count < 3
                      AND (cr.next_due_at IS NULL OR cr.next_due_at <= CURRENT_TIMESTAMP);
                """)
                return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            print(f"Error fetching due reminders: {e}")
            return []

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

    def get_next_invoice_number(self, user_id, insurer_name, date_str=None, workspace_admin_id=None):
        import re
        from datetime import datetime

        if not insurer_name:
            insurer_name = "Company"

        known_map = {
            "oriental insurance company limited": "OICL",
            "oriental insurance company": "OIC",
            "national insurance company": "NIC",
            "reliance general insurance co. ltd.": "RGI",
            "reliance general insurance": "RGI",
            "united india insurance": "UIIC",
            "new india assurance": "NIA"
        }
        clean_name = insurer_name.strip().lower()
        prefix_code = None
        for key, val in known_map.items():
            if key in clean_name:
                prefix_code = val
                break

        if not prefix_code:
            words = [w for w in re.findall(r'[A-Za-z0-9]+', insurer_name) if w.lower() not in ('co', 'ltd', 'limited')]
            if words:
                prefix_code = "".join([w[0].upper() for w in words])
            else:
                prefix_code = "BILL"

        dt = datetime.now()
        if date_str:
            for fmt in ('%Y-%m-%d', '%d.%m.%Y', '%d-%m-%Y'):
                try:
                    dt = datetime.strptime(date_str, fmt)
                    break
                except ValueError:
                    pass

        month_str = dt.strftime('%b').upper()
        year_str = dt.strftime('%y')
        pattern = f"{prefix_code}/{month_str}-{year_str}/"

        max_seq = 0

        scope_column = 'workspace_admin_id' if workspace_admin_id else 'user_id'
        scope_value = workspace_admin_id or user_id
        if self.conn:
            try:
                with self.conn.cursor() as cur:
                    cur.execute(f"""
                        SELECT invoice_no FROM fee_bills
                        WHERE {scope_column} = %s AND invoice_no LIKE %s
                    """, (int(scope_value) if str(scope_value).isdigit() else 1, f"{pattern}%"))
                    rows = cur.fetchall()
                    for r in rows:
                        inv = r['invoice_no'] if isinstance(r, dict) else r[0]
                        m = re.search(rf"{re.escape(pattern)}(\d+)", inv)
                        if m:
                            max_seq = max(max_seq, int(m.group(1)))

                    cur.execute(f"""
                        SELECT report_no FROM reports
                        WHERE {scope_column} = %s AND report_no LIKE %s
                    """, (int(scope_value) if str(scope_value).isdigit() else 1, f"{pattern}%"))
                    rows2 = cur.fetchall()
                    for r in rows2:
                        inv = r['report_no'] if isinstance(r, dict) else r[0]
                        m = re.search(rf"{re.escape(pattern)}(\d+)", inv)
                        if m:
                            max_seq = max(max_seq, int(m.group(1)))
            except Exception as e:
                print(f"Error querying invoice sequence: {e}")

        if hasattr(self, '_memory_fee_bills'):
            for b in self._memory_fee_bills:
                memory_scope = b.get('workspace_admin_id') if workspace_admin_id else b.get('user_id')
                if str(memory_scope) == str(scope_value) and b.get('invoice_no', '').startswith(pattern):
                    m = re.search(rf"{re.escape(pattern)}(\d+)", b.get('invoice_no'))
                    if m:
                        max_seq = max(max_seq, int(m.group(1)))

        next_seq = max_seq + 1
        return f"{pattern}{next_seq:02d}"

    def save_fee_bill(self, user_id, bill_data, workspace_admin_id=None):
        """Save a fee register row and mirror it to a linked workspace report in one transaction."""
        bill_id = bill_data.get('id') or str(uuid.uuid4())
        invoice_no = bill_data.get('invoice_no') or self.get_next_invoice_number(
            user_id, bill_data.get('insurer_name', 'Company'), bill_data.get('invoice_date'), workspace_admin_id=workspace_admin_id)
        invoice_date = bill_data.get('invoice_date', datetime.now().strftime('%Y-%m-%d'))
        insurer_name = bill_data.get('insurer_name', '')
        insured_name = bill_data.get('insured_name', '')
        policy_no = bill_data.get('policy_no', '')
        claim_no = bill_data.get('claim_no', '')
        vehicle_no = bill_data.get('vehicle_no', '')
        survey_type = bill_data.get('survey_type', 'Survey Fee')
        insurer_gst = bill_data.get('insurer_gst', '')
        insurer_state = bill_data.get('insurer_state', '')
        insurer_address = bill_data.get('insurer_address', '')
        professional_fee = float(bill_data.get('professional_fee', bill_data.get('taxable_amount', 0.0)) or 0)
        convenience_type = bill_data.get('convenience_type', '1st Convenience')
        convenience_route = bill_data.get('convenience_route', '')
        convenience_km = float(bill_data.get('convenience_km', 0.0) or 0)
        convenience_rate = float(bill_data.get('convenience_rate', 0.0) or 0)
        conveyance_fee = float(bill_data.get('conveyance_fee', bill_data.get('convenience_fee', convenience_km * convenience_rate)) or 0)
        photocopy_amount = float(bill_data.get('photocopy_amount', bill_data.get('photocopy', 0.0)) or 0)
        taxable_amount = float(bill_data.get('taxable_amount', professional_fee + conveyance_fee + photocopy_amount) or 0)
        gst_pc = float(bill_data.get('gst_pc', 18.0) or 0)
        gst_amount = float(bill_data.get('gst_amount', taxable_amount * (gst_pc / 100.0)) or 0)
        gross_invoice_value = float(bill_data.get('gross_invoice_value', bill_data.get('total_amount', taxable_amount + gst_amount)) or 0)
        tds_amount = float(bill_data.get('tds_amount', 0.0) or 0)
        amount_received = float(bill_data.get('amount_received', 0.0) or 0)
        outstanding_amount = float(bill_data.get('outstanding_amount', 0.0) or 0)
        due_date = bill_data.get('due_date') or None
        payment_status = bill_data.get('payment_status', 'unpaid') or 'unpaid'
        invoice_status = bill_data.get('invoice_status', 'draft') or 'draft'
        report_id = bill_data.get('report_id') or None
        created_at = datetime.now().isoformat()
        fee_breakdown = {
            'survey_type': survey_type,
            'insurer_gst': insurer_gst,
            'insurer_state': insurer_state,
            'insurer_address': insurer_address,
            'professional_fee': professional_fee,
            'convenience_type': convenience_type,
            'convenience_route': convenience_route,
            'convenience_km': convenience_km,
            'convenience_rate': convenience_rate,
            'conveyance_fee': conveyance_fee,
            'photocopy_amount': photocopy_amount,
            'taxable_amount': taxable_amount,
            'gst_pc': gst_pc,
            'gst_amount': gst_amount,
            'gross_invoice_value': gross_invoice_value,
            'tds_amount': tds_amount,
            'amount_received': amount_received,
            'outstanding_amount': outstanding_amount,
            'due_date': due_date,
            'payment_status': payment_status,
            'invoice_status': invoice_status,
            'invoice_no': invoice_no,
            'invoice_date': invoice_date,
            'fee_updated_at': created_at,
        }
        merged_data = dict(bill_data)
        merged_data.update(fee_breakdown)
        merged_data['report_id'] = report_id
        record = {
            'id': bill_id, 'user_id': str(user_id), 'workspace_admin_id': workspace_admin_id,
            'report_id': report_id, 'invoice_no': invoice_no, 'invoice_date': invoice_date,
            'survey_type': survey_type, 'insurer_gst': insurer_gst, 'insurer_state': insurer_state,
            'insurer_address': insurer_address,
            'insurer_name': insurer_name, 'insured_name': insured_name, 'policy_no': policy_no,
            'claim_no': claim_no, 'vehicle_no': vehicle_no, 'taxable_amount': taxable_amount,
            'professional_fee': professional_fee, 'convenience_type': convenience_type,
            'convenience_route': convenience_route,
            'convenience_km': convenience_km, 'convenience_rate': convenience_rate,
            'conveyance_fee': conveyance_fee, 'photocopy_amount': photocopy_amount,
            'gst_pc': gst_pc, 'gst_amount': gst_amount,
            'total_amount': gross_invoice_value, 'gross_invoice_value': gross_invoice_value,
            'tds_amount': tds_amount, 'amount_received': amount_received,
            'outstanding_amount': outstanding_amount, 'due_date': due_date,
            'payment_status': payment_status, 'invoice_status': invoice_status,
            'fee_updated_at': created_at, 'created_at': created_at, 'bill_data_json': merged_data,
        }
        if not self.conn:
            self.connect()
        if not self.conn:
            if not hasattr(self, '_memory_fee_bills'):
                self._memory_fee_bills = []
            self._memory_fee_bills = [b for b in self._memory_fee_bills if b.get('id') != bill_id]
            self._memory_fee_bills.append(record)
            return bill_id
        conn = self.conn
        was_autocommit = conn.autocommit
        saved = False
        try:
            if was_autocommit:
                conn.autocommit = False
            u_id = int(user_id) if str(user_id).isdigit() else 1
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                report_data = None
                if report_id and workspace_admin_id:
                    cur.execute("""
                        SELECT report_data_json FROM reports
                        WHERE id = %s AND workspace_admin_id = %s FOR UPDATE;
                    """, (report_id, workspace_admin_id))
                    linked_report = cur.fetchone()
                    if not linked_report:
                        raise ValueError('The linked report does not belong to this workspace.')
                    report_data = linked_report.get('report_data_json') or {}
                    if isinstance(report_data, str):
                        report_data = json.loads(report_data or '{}')
                cur.execute("""
                    INSERT INTO fee_bills (
                        id, user_id, workspace_admin_id, report_id, invoice_no, invoice_date,
                        insurer_name, insured_name, policy_no, claim_no, vehicle_no, taxable_amount,
                        professional_fee, gst_pc, gst_amount, total_amount, gross_invoice_value,
                        tds_amount, amount_received, outstanding_amount, due_date, payment_status,
                        invoice_status, fee_updated_at, bill_data_json
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, %s::jsonb)
                    ON CONFLICT (id) DO UPDATE SET
                        workspace_admin_id = EXCLUDED.workspace_admin_id, report_id = EXCLUDED.report_id,
                        invoice_no = EXCLUDED.invoice_no, invoice_date = EXCLUDED.invoice_date,
                        insurer_name = EXCLUDED.insurer_name, insured_name = EXCLUDED.insured_name,
                        policy_no = EXCLUDED.policy_no, claim_no = EXCLUDED.claim_no, vehicle_no = EXCLUDED.vehicle_no,
                        taxable_amount = EXCLUDED.taxable_amount, professional_fee = EXCLUDED.professional_fee,
                        gst_pc = EXCLUDED.gst_pc, gst_amount = EXCLUDED.gst_amount,
                        total_amount = EXCLUDED.total_amount, gross_invoice_value = EXCLUDED.gross_invoice_value,
                        tds_amount = EXCLUDED.tds_amount, amount_received = EXCLUDED.amount_received,
                        outstanding_amount = EXCLUDED.outstanding_amount, due_date = EXCLUDED.due_date,
                        payment_status = EXCLUDED.payment_status, invoice_status = EXCLUDED.invoice_status,
                        fee_updated_at = CURRENT_TIMESTAMP, bill_data_json = EXCLUDED.bill_data_json
                    WHERE fee_bills.workspace_admin_id = EXCLUDED.workspace_admin_id
                       OR (fee_bills.workspace_admin_id IS NULL AND EXCLUDED.workspace_admin_id IS NULL
                           AND fee_bills.user_id = EXCLUDED.user_id)
                    RETURNING id;
                """, (bill_id, u_id, workspace_admin_id, report_id, invoice_no, invoice_date,
                      insurer_name, insured_name, policy_no, claim_no, vehicle_no, taxable_amount,
                      professional_fee, gst_pc, gst_amount, gross_invoice_value, gross_invoice_value,
                      tds_amount, amount_received, outstanding_amount, due_date, payment_status,
                      invoice_status, json.dumps(merged_data)))
                if not cur.fetchone():
                    raise ValueError('This fee bill belongs to another workspace.')
                if report_id and workspace_admin_id:
                    report_data['fee_breakdown'] = fee_breakdown
                    cur.execute("""
                        UPDATE reports SET report_data_json = %s::jsonb, updated_at = CURRENT_TIMESTAMP,
                            updated_by = %s WHERE id = %s AND workspace_admin_id = %s;
                    """, (json.dumps(report_data), u_id, report_id, workspace_admin_id))
            conn.commit()
            saved = True
        except Exception as e:
            try: conn.rollback()
            except Exception: pass
            print(f"Error saving fee bill to DB: {e}")
        finally:
            try: conn.autocommit = was_autocommit
            except Exception: pass
        if not saved:
            return None
        if not hasattr(self, '_memory_fee_bills'):
            self._memory_fee_bills = []
        self._memory_fee_bills = [b for b in self._memory_fee_bills if b.get('id') != bill_id]
        self._memory_fee_bills.append(record)
        return bill_id

    def get_user_fee_bills(self, user_id):
        results = []
        if self.conn:
            try:
                u_id = int(user_id) if str(user_id).isdigit() else 1
                with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("SELECT * FROM fee_bills WHERE user_id = %s ORDER BY created_at DESC", (u_id,))
                    rows = cur.fetchall()
                    for r in rows:
                        d = dict(r)
                        if isinstance(d.get('created_at'), datetime):
                            d['created_at'] = d['created_at'].isoformat()
                        results.append(d)
                    return results
            except Exception as e:
                print(f"Error fetching fee bills from DB: {e}")

        if hasattr(self, '_memory_fee_bills'):
            return [b for b in self._memory_fee_bills if str(b.get('user_id')) == str(user_id)]
        return []

    def get_workspace_fee_bills(self, workspace_admin_id, month=None, insurer=None, report_id=None):
        if not self.conn: self.connect()
        if not self.conn:
            return [b for b in getattr(self, '_memory_fee_bills', []) if b.get('workspace_admin_id') == workspace_admin_id]
        filters = ['workspace_admin_id = %s']
        params = [workspace_admin_id]
        if month:
            filters.append("TO_CHAR(invoice_date::date, 'YYYY-MM') = %s")
            params.append(month)
        if insurer:
            filters.append('insurer_name ILIKE %s')
            params.append(f"%{insurer.strip()}%")
        if report_id:
            filters.append('report_id = %s')
            params.append(report_id)
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(f"SELECT * FROM fee_bills WHERE {' AND '.join(filters)} ORDER BY invoice_date DESC, created_at DESC;", tuple(params))
                results = []
                for row in cur.fetchall():
                    item = dict(row)
                    if isinstance(item.get('bill_data_json'), dict):
                        bd = item['bill_data_json']
                        for k, v in bd.items():
                            if k not in item or item[k] is None:
                                item[k] = v
                    for key in ('created_at', 'fee_updated_at', 'due_date'):
                        if isinstance(item.get(key), (datetime, date)):
                            item[key] = item[key].isoformat()
                    results.append(item)
                return results
        except Exception as e:
            print(f"Error fetching workspace fee bills: {e}")
            return []

    def delete_fee_bill(self, bill_id, user_id, workspace_admin_id=None):
        if hasattr(self, '_memory_fee_bills'):
            self._memory_fee_bills = [b for b in self._memory_fee_bills if b.get('id') != bill_id]

        if self.conn:
            try:
                u_id = int(user_id) if str(user_id).isdigit() else 1
                with self.conn.cursor() as cur:
                    if workspace_admin_id:
                        cur.execute("DELETE FROM fee_bills WHERE id = %s AND workspace_admin_id = %s", (bill_id, workspace_admin_id))
                    else:
                        cur.execute("DELETE FROM fee_bills WHERE id = %s AND user_id = %s", (bill_id, u_id))
                    return True
            except Exception as e:
                print(f"Error deleting fee bill: {e}")
                return False
        return True


    # --- Insurer Master CRUD & Auto-Fill ---
    def get_insurer_masters(self, workspace_admin_id):
        if not self.conn: self.connect()
        if not self.conn: return []
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT id, workspace_admin_id, insurer_name, branch_name, branch_address, gstin,
                           state_code, invoice_prefix, default_conveyance_rate, created_at, updated_at
                    FROM insurer_master
                    WHERE workspace_admin_id = %s
                    ORDER BY insurer_name ASC, branch_name ASC;
                """, (workspace_admin_id,))
                results = []
                for row in cur.fetchall():
                    item = dict(row)
                    for k in ('created_at', 'updated_at'):
                        if isinstance(item.get(k), (datetime, date)):
                            item[k] = item[k].isoformat()
                    results.append(item)
                return results
        except Exception as e:
            print(f"Error fetching insurer masters: {e}")
            return []

    def get_insurer_master_by_id(self, insurer_id, workspace_admin_id):
        if not self.conn: self.connect()
        if not self.conn: return None
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM insurer_master
                    WHERE id = %s AND workspace_admin_id = %s;
                """, (insurer_id, workspace_admin_id))
                row = cur.fetchone()
                if row:
                    item = dict(row)
                    for k in ('created_at', 'updated_at'):
                        if isinstance(item.get(k), (datetime, date)):
                            item[k] = item[k].isoformat()
                    return item
                return None
        except Exception as e:
            print(f"Error fetching insurer master by id: {e}")
            return None

    def save_insurer_master(self, workspace_admin_id, insurer_data):
        if not self.conn: self.connect()
        if not self.conn: return None
        insurer_name = str(insurer_data.get('insurer_name', '')).strip()
        branch_name = str(insurer_data.get('branch_name', '')).strip()
        branch_address = str(insurer_data.get('branch_address', '')).strip()
        gstin = str(insurer_data.get('gstin', '')).strip()
        state_code = str(insurer_data.get('state_code', '19')).strip()
        invoice_prefix = str(insurer_data.get('invoice_prefix', '')).strip().upper()
        try:
            default_conveyance_rate = float(insurer_data.get('default_conveyance_rate', 10.0))
        except (ValueError, TypeError):
            default_conveyance_rate = 10.0

        insurer_id = insurer_data.get('id')
        try:
            with self.conn.cursor() as cur:
                if insurer_id:
                    cur.execute("""
                        UPDATE insurer_master SET
                            insurer_name = %s, branch_name = %s, branch_address = %s,
                            gstin = %s, state_code = %s, invoice_prefix = %s, default_conveyance_rate = %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s AND workspace_admin_id = %s
                        RETURNING id;
                    """, (insurer_name, branch_name, branch_address, gstin, state_code, invoice_prefix,
                          default_conveyance_rate, insurer_id, workspace_admin_id))
                    res = cur.fetchone()
                    return res[0] if res else None
                else:
                    cur.execute("""
                        INSERT INTO insurer_master (
                            workspace_admin_id, insurer_name, branch_name, branch_address,
                            gstin, state_code, invoice_prefix, default_conveyance_rate
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (workspace_admin_id, insurer_name, branch_name) DO UPDATE SET
                            branch_address = EXCLUDED.branch_address,
                            gstin = EXCLUDED.gstin,
                            state_code = EXCLUDED.state_code,
                            invoice_prefix = EXCLUDED.invoice_prefix,
                            default_conveyance_rate = EXCLUDED.default_conveyance_rate,
                            updated_at = CURRENT_TIMESTAMP
                        RETURNING id;
                    """, (workspace_admin_id, insurer_name, branch_name, branch_address, gstin, state_code,
                          invoice_prefix, default_conveyance_rate))
                    res = cur.fetchone()
                    return res[0] if res else None
        except Exception as e:
            print(f"Error saving insurer master: {e}")
            return None

    def delete_insurer_master(self, insurer_id, workspace_admin_id):
        if not self.conn: self.connect()
        if not self.conn: return False
        try:
            with self.conn.cursor() as cur:
                cur.execute("DELETE FROM insurer_master WHERE id = %s AND workspace_admin_id = %s RETURNING id;",
                            (insurer_id, workspace_admin_id))
                return cur.fetchone() is not None
        except Exception as e:
            print(f"Error deleting insurer master: {e}")
            return False

    def get_next_insurer_invoice_number(self, workspace_admin_id, prefix):
        if not prefix:
            prefix = "BILL"
        prefix = prefix.strip().upper()
        if not self.conn: self.connect()
        if not self.conn: return f"{prefix}-1"
        try:
            with self.conn.cursor() as cur:
                # Find maximum numeric sequence for this insurer prefix
                pattern = f"{prefix}-%"
                cur.execute("""
                    SELECT invoice_no FROM fee_bills
                    WHERE workspace_admin_id = %s AND (insurer_prefix = %s OR invoice_no ILIKE %s);
                """, (workspace_admin_id, prefix, pattern))
                rows = cur.fetchall()
                max_seq = 0
                for r in rows:
                    inv_str = str(r[0] or '')
                    if '-' in inv_str:
                        parts = inv_str.split('-')
                        if parts[-1].isdigit():
                            seq = int(parts[-1])
                            if seq > max_seq:
                                max_seq = seq
                return f"{prefix}-{max_seq + 1}"
        except Exception as e:
            print(f"Error calculating next insurer invoice number: {e}")
            return f"{prefix}-1"

    # --- Gmail Intimations Staging ---
    def get_staged_gmail_intimations(self, workspace_admin_id, status='pending'):
        if not self.conn: self.connect()
        if not self.conn: return []
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM gmail_intimations_staging
                    WHERE workspace_admin_id = %s AND (%s IS NULL OR status = %s)
                    ORDER BY received_at DESC;
                """, (workspace_admin_id, status, status))
                results = []
                for row in cur.fetchall():
                    item = dict(row)
                    if isinstance(item.get('received_at'), (datetime, date)):
                        item['received_at'] = item['received_at'].isoformat()
                    if isinstance(item.get('created_at'), (datetime, date)):
                        item['created_at'] = item['created_at'].isoformat()
                    results.append(item)
                return results
        except Exception as e:
            print(f"Error reading staged Gmail intimations: {e}")
            return []

    def save_staged_gmail_intimation(self, workspace_admin_id, data):
        if not self.conn: self.connect()
        if not self.conn: return None
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO gmail_intimations_staging (
                        workspace_admin_id, gmail_message_id, sender_email, subject, received_at,
                        extracted_claim_no, extracted_insured_name, extracted_vehicle_no,
                        extracted_policy_no, extracted_insurer_name, raw_body, status
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending')
                    ON CONFLICT (workspace_admin_id, gmail_message_id) DO UPDATE SET
                        sender_email = EXCLUDED.sender_email,
                        subject = EXCLUDED.subject,
                        extracted_claim_no = EXCLUDED.extracted_claim_no,
                        extracted_insured_name = EXCLUDED.extracted_insured_name,
                        extracted_vehicle_no = EXCLUDED.extracted_vehicle_no,
                        extracted_policy_no = EXCLUDED.extracted_policy_no,
                        extracted_insurer_name = EXCLUDED.extracted_insurer_name,
                        raw_body = EXCLUDED.raw_body
                    RETURNING id;
                """, (
                    workspace_admin_id, data.get('gmail_message_id'), data.get('sender_email'),
                    data.get('subject'), data.get('received_at'), data.get('extracted_claim_no'),
                    data.get('extracted_insured_name'), data.get('extracted_vehicle_no'),
                    data.get('extracted_policy_no'), data.get('extracted_insurer_name'),
                    data.get('raw_body')
                ))
                res = cur.fetchone()
                return res[0] if res else None
        except Exception as e:
            print(f"Error saving staged Gmail intimation: {e}")
            return None

    def update_staged_gmail_intimation_status(self, intimation_id, workspace_admin_id, status):
        if not self.conn: self.connect()
        if not self.conn: return False
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    UPDATE gmail_intimations_staging SET status = %s
                    WHERE id = %s AND workspace_admin_id = %s
                    RETURNING id;
                """, (status, intimation_id, workspace_admin_id))
                return cur.fetchone() is not None
        except Exception as e:
            print(f"Error updating staged Gmail intimation status: {e}")
            return False


db = PostgresDB()

