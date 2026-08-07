#!/usr/bin/env bash
# Diagnostic & Fix script for Hostinger VPS 500 Error Resolution

set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

printf '%b\n' "${YELLOW}=== Step 1: Inspecting current system logs & service statuses ===${NC}"
sudo journalctl -u insurance -n 30 --no-pager || true
sudo systemctl status insurance redis-server nginx --no-pager || true

printf '%b\n' "${YELLOW}=== Step 2: Ensuring Redis service is active ===${NC}"
sudo systemctl enable redis-server
sudo systemctl restart redis-server

printf '%b\n' "${YELLOW}=== Step 3: Checking /etc/insurance/insurance.env ===${NC}"
ENV_FILE="/etc/insurance/insurance.env"

if [[ ! -f "$ENV_FILE" ]]; then
    printf '%b\n' "${RED}Error: $ENV_FILE does not exist! Creating default...${NC}"
    sudo touch "$ENV_FILE"
    sudo chmod 640 "$ENV_FILE"
    sudo chown root:insurance "$ENV_FILE"
fi

# Ensure CREDENTIAL_ENCRYPTION_KEY exists
if ! grep -q '^CREDENTIAL_ENCRYPTION_KEY=' "$ENV_FILE" || grep -q '^CREDENTIAL_ENCRYPTION_KEY=$' "$ENV_FILE"; then
    printf '%b\n' "${YELLOW}Generating missing CREDENTIAL_ENCRYPTION_KEY...${NC}"
    FERNET_KEY=$(/var/www/insurance-app/venv/bin/python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
    echo "CREDENTIAL_ENCRYPTION_KEY=$FERNET_KEY" | sudo tee -a "$ENV_FILE" >/dev/null
    printf '%b\n' "${GREEN}Added CREDENTIAL_ENCRYPTION_KEY to $ENV_FILE${NC}"
fi

# Ensure RATELIMIT_STORAGE_URI exists
if ! grep -q '^RATELIMIT_STORAGE_URI=' "$ENV_FILE"; then
    printf '%b\n' "${YELLOW}Adding default RATELIMIT_STORAGE_URI...${NC}"
    echo "RATELIMIT_STORAGE_URI=redis://127.0.0.1:6379/0" | sudo tee -a "$ENV_FILE" >/dev/null
fi

# Ensure FLASK_SECRET_KEY exists
if ! grep -q '^FLASK_SECRET_KEY=' "$ENV_FILE"; then
    printf '%b\n' "${YELLOW}Generating missing FLASK_SECRET_KEY...${NC}"
    SECRET_KEY=$(/var/www/insurance-app/venv/bin/python -c "import secrets; print(secrets.token_hex(32))")
    echo "FLASK_SECRET_KEY=$SECRET_KEY" | sudo tee -a "$ENV_FILE" >/dev/null
fi

# Ensure FLASK_ENV=production exists
if ! grep -q '^FLASK_ENV=' "$ENV_FILE"; then
    echo "FLASK_ENV=production" | sudo tee -a "$ENV_FILE" >/dev/null
fi

printf '%b\n' "${YELLOW}=== Step 4: Restarting application services ===${NC}"
sudo systemctl restart insurance
sudo systemctl restart insurance-worker
sudo systemctl reload nginx

printf '%b\n' "${YELLOW}=== Step 5: Verification ===${NC}"
sleep 2
printf 'Checking Gunicorn service status: '
if systemctl is-active --quiet insurance; then
    printf '%b\n' "${GREEN}ACTIVE${NC}"
else
    printf '%b\n' "${RED}FAILED${NC}"
    sudo journalctl -u insurance -n 40 --no-pager
    exit 1
fi

printf 'Testing https://skinsurance.tech/healthz: '
HEALTHZ_STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://skinsurance.tech/healthz || true)
if [[ "$HEALTHZ_STATUS" == "200" ]]; then
    printf '%b\n' "${GREEN}HTTP 200 OK${NC}"
else
    printf '%b\n' "${RED}HTTP $HEALTHZ_STATUS${NC}"
fi

printf 'Testing https://skinsurance.tech/login: '
LOGIN_STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://skinsurance.tech/login || true)
if [[ "$LOGIN_STATUS" == "200" ]]; then
    printf '%b\n' "${GREEN}HTTP 200 OK${NC}"
else
    printf '%b\n' "${RED}HTTP $LOGIN_STATUS${NC}"
fi

printf '%b\n' "${GREEN}=== Diagnostics & Fix Script Completed ===${NC}"
