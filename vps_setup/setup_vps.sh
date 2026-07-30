#!/usr/bin/env bash
# Initial provisioning helper for an Ubuntu 24.04 VPS.
# Supply DB_PASSWORD through a protected shell/session; it is never stored here.

set -euo pipefail

if [[ -z "${DB_PASSWORD:-}" ]]; then
    read -r -s -p "PostgreSQL password for insurance_user: " DB_PASSWORD
    echo
fi

echo "=== Updating packages ==="
sudo apt update
sudo apt upgrade -y

echo "=== Installing system dependencies ==="
sudo apt install -y python3-pip python3-venv python3-dev postgresql postgresql-contrib nginx certbot python3-certbot-nginx git

echo "=== Configuring PostgreSQL ==="
sudo systemctl enable --now postgresql

if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname = 'insurance_user'" | grep -q 1; then
    sudo -u postgres psql -v ON_ERROR_STOP=1 -v db_password="$DB_PASSWORD" -c "CREATE USER insurance_user WITH PASSWORD :'db_password';"
fi

if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname = 'insurance_db'" | grep -q 1; then
    sudo -u postgres createdb -O insurance_user insurance_db
fi

sudo -u postgres psql -v ON_ERROR_STOP=1 -c "GRANT ALL PRIVILEGES ON DATABASE insurance_db TO insurance_user;"
unset DB_PASSWORD

echo "=== Creating application directory ==="
sudo mkdir -p /var/www/insurance-app
sudo chown -R "$USER:$USER" /var/www/insurance-app

cat <<'ENV_TEMPLATE'
Create /var/www/insurance-app/.env with mode 600 and values provided through your
secret manager. Do not add this file to Git:

DATABASE_URL=postgresql://insurance_user:<url-encoded-password>@127.0.0.1:5432/insurance_db
FLASK_SECRET_KEY=<long-random-secret>
GEMINI_API_KEY=<gemini-api-key>
GOOGLE_SHEETS_CREDENTIALS=<service-account-json>
GOOGLE_DRIVE_FOLDER_ID=<drive-folder-id>
GMAIL_TOKEN_ENCRYPTION_KEY=<fernet-key>
GMAIL_OAUTH_CLIENT_ID=<oauth-client-id>
GMAIL_OAUTH_CLIENT_SECRET=<oauth-client-secret>
GMAIL_OAUTH_REDIRECT_URI=https://skinsurance.tech/auth/gmail/callback
ENV_TEMPLATE

echo "=== Setup complete ==="
echo "Install the application dependencies, copy the systemd and Nginx configuration, then start the services."
