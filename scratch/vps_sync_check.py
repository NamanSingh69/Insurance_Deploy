import paramiko
import sys

def main():
    hostname = '185.199.52.85'
    port = 22
    username = 'root'
    password = 'surveyorportal@2026'

    print(f"Connecting to VPS {hostname}...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname, port=port, username=username, password=password, timeout=10)

    commands = [
        "cd /var/www/insurance-app && git log -n 1 --oneline",
        "cd /var/www/insurance-app && git pull --ff-only origin main",
        "cd /var/www/insurance-app && systemctl restart insurance && systemctl restart insurance-worker && systemctl reload nginx",
        "cd /var/www/insurance-app && git log -n 1 --oneline",
        "systemctl is-active insurance",
        "systemctl is-active nginx",
        "curl -fsS -o /dev/null -w '%{http_code}\\n' https://skinsurance.tech/login"
    ]

    for cmd in commands:
        print(f"\n--- Running: {cmd} ---")
        stdin, stdout, stderr = client.exec_command(cmd)
        out = stdout.read().decode('utf-8')
        err = stderr.read().decode('utf-8')
        if out:
            print(f"STDOUT:\n{out.strip()}")
        if err:
            print(f"STDERR:\n{err.strip()}")

    client.close()

if __name__ == '__main__':
    main()
