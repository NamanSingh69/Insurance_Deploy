#!/bin/bash
# ==============================================================================
# Automated VPS Deployment Script - Motor Survey Report Generator
# Location: /var/www/insurance-app/vps_setup/auto_deploy.sh
# Triggered by: GitHub Webhook (/api/deploy-webhook) or CLI
# ==============================================================================

set -e

APP_DIR="/var/www/insurance-app"
LOG_FILE="$APP_DIR/deploy.log"
TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")

log() {
    echo "[$TIMESTAMP] $1" | tee -a "$LOG_FILE" 2>/dev/null || echo "[$TIMESTAMP] $1"
}

log "=== Starting Automated Deployment ==="

cd "$APP_DIR"

# 1. Pull latest code from GitHub with safe.directory override
log "Fetching latest changes from origin/main..."
git config --system --add safe.directory "$APP_DIR" 2>/dev/null || true
git -c safe.directory="$APP_DIR" remote set-url origin https://github.com/NamanSingh69/Insurance_Deploy.git 2>/dev/null || true
git -c safe.directory="$APP_DIR" fetch origin main
PREV_COMMIT=$(git -c safe.directory="$APP_DIR" rev-parse --short HEAD || echo "unknown")
git -c safe.directory="$APP_DIR" reset --hard origin/main
NEW_COMMIT=$(git -c safe.directory="$APP_DIR" rev-parse --short HEAD || echo "unknown")
log "Updated from commit $PREV_COMMIT to $NEW_COMMIT"

# 2. Make scripts executable and configure daily backup cron
chmod +x "$APP_DIR/vps_setup/"*.sh 2>/dev/null || true
if [ -d "/etc/cron.daily" ] && [ -f "$APP_DIR/vps_setup/backup_cron.sh" ]; then
    ln -sf "$APP_DIR/vps_setup/backup_cron.sh" /etc/cron.daily/backup_insurance_db 2>/dev/null || true
    log "Configured daily database backup cron (/etc/cron.daily/backup_insurance_db)."
fi

# Ensure Certbot SSL renewal timer is enabled
systemctl enable --now certbot.timer 2>/dev/null || true

# 3. Update Python dependencies if requirements.txt exists
if [ -f "$APP_DIR/venv/bin/activate" ]; then
    log "Synchronizing Python virtual environment dependencies..."
    source "$APP_DIR/venv/bin/activate"
    pip install -r requirements.txt --quiet || true
elif [ -f "$APP_DIR/.venv/bin/activate" ]; then
    log "Synchronizing Python virtual environment dependencies (.venv)..."
    source "$APP_DIR/.venv/bin/activate"
    pip install -r requirements.txt --quiet || true
fi

# 4. Restart services
log "Reloading application services..."
if sudo systemctl restart insurance.service insurance-worker.service nginx.service 2>/dev/null; then
    log "Restarted via sudo systemctl."
elif systemctl restart insurance.service insurance-worker.service nginx.service 2>/dev/null; then
    log "Restarted via systemctl."
else
    log "Falling back to SIGHUP reload for Gunicorn and worker refresh..."
    pkill -HUP -f gunicorn || true
    pkill -f "python.*worker.py" || true
fi

# 5. Verify local health check
log "Verifying application liveness..."
sleep 2
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/healthz || curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1/healthz || echo "000")

if [ "$HTTP_CODE" = "200" ]; then
    log "HEALTH CHECK PASSED: Internal healthz returned HTTP 200 OK."
    log "=== Deployment SUCCESSFUL (Commit: $NEW_COMMIT) ==="
    exit 0
else
    log "HEALTH CHECK WARNING: Expected HTTP 200, got $HTTP_CODE."
    log "=== Deployment completed with health check warning ==="
    exit 0
fi
