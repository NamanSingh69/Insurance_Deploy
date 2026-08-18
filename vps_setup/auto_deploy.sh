#!/bin/bash
# ==============================================================================
# Automated VPS Deployment Script - Motor Survey Report Generator
# Location: /var/www/insurance-app/vps_setup/auto_deploy.sh
# Triggered by: GitHub Webhook (/api/deploy-webhook) or CLI
# ==============================================================================

set +e

APP_DIR="/var/www/insurance-app"
LOG_FILE="$APP_DIR/deploy.log"
TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")

log() {
    echo "[$TIMESTAMP] $1" | tee -a "$LOG_FILE" 2>/dev/null || echo "[$TIMESTAMP] $1"
}

log "=== Starting Automated Deployment ==="

cd "$APP_DIR"

if [ -f "/etc/insurance/insurance.env" ]; then
    set -a
    source "/etc/insurance/insurance.env"
    set +a
fi

# 1. Pull latest code from GitHub if not in bundle mode
if [ "$1" = "bundle" ] || [ -f "$APP_DIR/.bundle_deploy" ]; then
    log "Bundle mode active; skipping git fetch/reset and preserving extracted files."
    rm -f "$APP_DIR/.bundle_deploy" 2>/dev/null || true
else
    log "Checking for Git updates..."
    if git -c safe.directory="*" fetch origin main 2>/dev/null; then
        PREV_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
        git -c safe.directory="*" reset --hard origin/main 2>/dev/null || true
        NEW_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
        log "Updated from commit $PREV_COMMIT to $NEW_COMMIT"
    else
        log "Git fetch failed or offline; keeping current directory."
    fi
fi

# 2. Make scripts executable and configure daily backup cron
chmod +x "$APP_DIR/vps_setup/"*.sh 2>/dev/null || true
if [ -d "/etc/cron.daily" ] && [ -f "$APP_DIR/vps_setup/backup_cron.sh" ]; then
    ln -sf "$APP_DIR/vps_setup/backup_cron.sh" /etc/cron.daily/backup_insurance_db 2>/dev/null || true
fi

# 3. Update Python dependencies & apply database migrations
if [ -f "$APP_DIR/venv/bin/activate" ]; then
    source "$APP_DIR/venv/bin/activate"
    python -c "from dotenv import load_dotenv; load_dotenv('/etc/insurance/insurance.env'); from db import db; db.connect(); db._ensure_default_users();" 2>&1 | tee -a "$LOG_FILE" || true
elif [ -f "$APP_DIR/.venv/bin/activate" ]; then
    source "$APP_DIR/.venv/bin/activate"
    python -c "from dotenv import load_dotenv; load_dotenv('/etc/insurance/insurance.env'); from db import db; db.connect(); db._ensure_default_users();" 2>&1 | tee -a "$LOG_FILE" || true
fi

# 4. Restart services
log "Reloading application services..."
if sudo /bin/systemctl restart insurance.service insurance-worker.service nginx.service 2>/dev/null; then
    log "Restarted via sudo /bin/systemctl."
elif sudo systemctl restart insurance.service insurance-worker.service nginx.service 2>/dev/null; then
    log "Restarted via sudo systemctl."
else
    log "Restarting processes via process termination..."
    pkill -HUP -f gunicorn || true
    pkill -TERM -f gunicorn || true
    pkill -TERM -f "python.*worker.py" || true
    sleep 2
    pkill -9 -f gunicorn || true
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
