import csv
import json
import os
from datetime import datetime
from db import db

def run_migration():
    print("Connecting to Supabase PostgreSQL database...")
    db.connect()
    if not db.conn:
        print("Failed to connect to database. Please check DATABASE_URL in .env.")
        return

    # 1. Migrate Users
    users_file = 'InsuranceAppDB - Users.csv'
    if os.path.exists(users_file):
        print(f"Migrating users from {users_file}...")
        with open(users_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                # Convert strings to appropriate types
                try:
                    user_data = {
                        'id': int(row['id']) if row['id'] else None,
                        'username': row['username'],
                        'password_hash': row['password_hash'],
                        'full_name': row['full_name'],
                        'qualifications': row['qualifications'],
                        'designation': row['designation'],
                        'license_no': row['license_no'],
                        'expiry_date': row['expiry_date'],
                        'membership_no': row['membership_no'],
                        'address_line_1': row['address_line_1'],
                        'address_line_2': row['address_line_2'],
                        'address_line_3': row['address_line_3'],
                        'contact_no': row['contact_no'],
                        'email': row['email']
                    }
                    
                    if not user_data['id'] or not user_data['username']:
                        continue

                    # Check if user already exists
                    existing = db.get_user_by_id(user_data['id'])
                    if not existing:
                        db.create_user(user_data)
                        count += 1
                except Exception as e:
                    print(f"Error migrating user {row.get('username')}: {e}")
            print(f"Successfully migrated {count} users.")
    else:
        print(f"{users_file} not found.")

    # 2. Migrate Reports
    reports_file = 'InsuranceAppDB - Reports.csv'
    if os.path.exists(reports_file):
        print(f"Migrating reports from {reports_file}. This might take a minute...")
        with open(reports_file, 'r', encoding='utf-8') as f:
            # Increase field size limit for giant JSON chunks
            csv.field_size_limit(2147483647)
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                try:
                    rid = row.get('id')
                    user_id_str = row.get('user_id')
                    if not rid or not user_id_str:
                        continue
                        
                    user_id = int(user_id_str)
                    report_no = row.get('report_no', '')
                    insured_name = row.get('insured_name', '')
                    vehicle_no = row.get('vehicle_no', '')
                    claim_no = row.get('claim_no', '')
                    policy_no = row.get('policy_no', '')
                    saved_at_str = row.get('saved_at', '')
                    
                    include_in_consolidated = str(row.get('include_in_consolidated', 'True')).lower() == 'true'

                    # Reassemble JSON chunks
                    json_chunks = []
                    json_chunks.append(row.get('report_data_json', ''))
                    for i in range(2, 1001):
                        key = f"report_data_json_{i}"
                        if key in row:
                            json_chunks.append(row[key])
                    
                    full_json_str = ''.join([c for c in json_chunks if c])
                    
                    if not full_json_str:
                        continue

                    try:
                        report_data_json = json.loads(full_json_str)
                    except json.JSONDecodeError as e:
                        print(f"Error parsing JSON for report {rid}: {e}")
                        continue

                    if saved_at_str:
                        try:
                            saved_at = datetime.fromisoformat(saved_at_str)
                        except ValueError:
                            saved_at = datetime.utcnow()
                    else:
                        saved_at = datetime.utcnow()

                    with db.conn.cursor() as cur:
                        cur.execute("SELECT id FROM reports WHERE id = %s;", (rid,))
                        if not cur.fetchone():
                            cur.execute('''
                                INSERT INTO reports (
                                    id, user_id, report_no, insured_name, vehicle_no, claim_no, 
                                    policy_no, saved_at, include_in_consolidated, report_data_json
                                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb);
                            ''', (rid, user_id, report_no, insured_name, vehicle_no, claim_no, policy_no, saved_at, include_in_consolidated, json.dumps(report_data_json)))
                            count += 1
                except Exception as e:
                    print(f"Error migrating report {row.get('id')}: {e}")

            print(f"Successfully migrated {count} reports.")
    else:
        print(f"{reports_file} not found.")

if __name__ == "__main__":
    run_migration()
