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
sudo apt install -y python3-pip python3-venv python3-dev postgresql postgresql-contrib redis-server nginx certbot python3-certbot-nginx git

echo "=== Configuring PostgreSQL & Redis ==="
sudo systemctl enable --now postgresql
sudo systemctl enable --now redis-server

if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname = 'insurance_user'" | grep -q 1; then
    sudo -u postgres psql -v ON_ERROR_STOP=1 -v db_password="$DB_PASSWORD" -c "CREATE USER insurance_user WITH PASSWORD :'db_password';"
fi

if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname = 'insurance_db'" | grep -q 1; then
    sudo -u postgres createdb -O insurance_user insurance_db
fi

sudo -u postgres psql -v ON_ERROR_STOP=1 -c "GRANT ALL PRIVILEGES ON DATABASE insurance_db TO insurance_user;"
unset DB_PASSWORD

echo "=== Creating system user & directories ==="
if ! id -u insurance >/dev/null 2>&1; then
    sudo useradd -r -s /bin/false insurance
fi

sudo mkdir -p /var/www/insurance-app
sudo mkdir -p /var/lib/insurance/private_assets
sudo mkdir -p /etc/insurance

sudo chown -R insurance:insurance /var/www/insurance-app
sudo chown -R insurance:insurance /var/lib/insurance
sudo chmod 700 /var/lib/insurance/private_assets
sudo chown root:insurance /etc/insurance
sudo chmod 750 /etc/insurance

cat <<'ENV_TEMPLATE'
Create /etc/insurance/insurance.env with mode 640 (root:insurance) and secret values:

FLASK_ENV=production
DATABASE_URL=postgresql://insurance_user:<url-encoded-password>@127.0.0.1:5432/insurance_db
FLASK_SECRET_KEY=<generate-32-byte-hex-secret>
CREDENTIAL_ENCRYPTION_KEY=<generate-fernet-key-python-cryptography>
RATELIMIT_STORAGE_URI=redis://127.0.0.1:6379/0
PRIVATE_STORAGE_DIR=/var/lib/insurance/private_assets
GOOGLE_OAUTH_CLIENT_ID=<oauth-client-id>
GOOGLE_OAUTH_CLIENT_SECRET=<oauth-client-secret>
GOOGLE_OAUTH_REDIRECT_URI=https://skinsurance.tech/auth/google/callback
GMAIL_OAUTH_CLIENT_ID=<gmail-oauth-client-id>
GMAIL_OAUTH_CLIENT_SECRET=<gmail-oauth-client-secret>
GMAIL_OAUTH_REDIRECT_URI=https://skinsurance.tech/auth/gmail/callback
ENV_TEMPLATE

echo "=== Setup complete ==="
echo "Install the application dependencies, copy the systemd and Nginx configuration, run database migrations, then start the services."
