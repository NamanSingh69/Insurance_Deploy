import paramiko
import time
import sys

HOST = "185.199.52.85"
PORT = 22
USER = "root"
PASS = "surveyorportal@2026"

def run_ssh_commands():
    print(f"Connecting to VPS at {HOST}:{PORT} as {USER}...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, port=PORT, username=USER, password=PASS, timeout=30)
    print("SSH connection established successfully.\n")

    commands = [
        ("Create Backup Directory", "mkdir -p /root/backups"),
        ("Take PostgreSQL Snapshot Backup", "export PGPASSWORD='surveyorportal@2026' && pg_dump -U insurance_user -h localhost -d insurance_db > /root/backups/insurance_db_$(date +%Y%m%d_%H%M%S).sql && ls -lh /root/backups/"),
        ("Git Pull Main on VPS", "cd /var/www/insurance-app && git pull --ff-only origin main"),
        ("Pip Install Requirements", "cd /var/www/insurance-app && /var/www/insurance-app/venv/bin/pip install -r requirements.txt"),
        ("Restart Application Services", "systemctl restart insurance && systemctl restart insurance-worker && systemctl reload nginx"),
        ("Verify Service Status", "systemctl is-active insurance && systemctl is-active insurance-worker && systemctl is-active nginx"),
        ("Run Deployment Verification Script", "cd /var/www/insurance-app && export PGPASSWORD='surveyorportal@2026' && ./vps_setup/verify_deployment.sh"),
        ("Verify Public Endpoint", "curl -fsS -o /dev/null -w '%{http_code}\n' https://skinsurance.tech/login")
    ]

    all_passed = True
    for title, cmd in commands:
        print(f"--- [{title}] ---")
        print(f"$ {cmd}")
        stdin, stdout, stderr = client.exec_command(cmd, timeout=120)
        exit_status = stdout.channel.recv_exit_status()
        out = stdout.read().decode('utf-8', errors='replace').strip()
        err = stderr.read().decode('utf-8', errors='replace').strip()
        
        if out:
            print(f"STDOUT:\n{out}")
        if err:
            print(f"STDERR:\n{err}")
        print(f"Exit Code: {exit_status}\n")

        if exit_status != 0:
            print(f"[ERROR] Step '{title}' failed with code {exit_status}")
            all_passed = False
            break

    client.close()
    if not all_passed:
        sys.exit(1)
    print("ALL VPS DEPLOYMENT STEPS COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    run_ssh_commands()
