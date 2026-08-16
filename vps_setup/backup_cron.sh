#!/bin/bash
# ==============================================================================
# Automated Daily Database Backup & 14-Day Rotation Script
# Location: /var/www/insurance-app/vps_setup/backup_cron.sh
# Symlinked / Installed to: /etc/cron.daily/backup_insurance_db
# ==============================================================================

set -e

BACKUP_DIR="/root/backups"
DB_NAME="insurance_db"
DB_USER="insurance_user"
TIMESTAMP=$(date "+%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/insurance_db_daily_${TIMESTAMP}.sql.gz"
LOG_FILE="/var/log/insurance_backup.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# 1. Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

log "=== Starting Daily Database Backup ==="

# 2. Perform compressed pg_dump
export PGPASSWORD="surveyorportal@2026"
if pg_dump -U "$DB_USER" -h localhost -d "$DB_NAME" | gzip > "$BACKUP_FILE"; then
    FILESIZE=$(ls -lh "$BACKUP_FILE" | awk '{print $5}')
    log "Backup successful: $BACKUP_FILE (Size: $FILESIZE)"
else
    log "ERROR: pg_dump failed!"
    exit 1
fi

# 3. Clean up backups older than 14 days
log "Purging backup archives older than 14 days..."
DELETED_COUNT=$(find "$BACKUP_DIR" -name "insurance_db_*.sql.gz" -mtime +14 -delete -print 2>/dev/null | wc -l)
log "Removed $DELETED_COUNT expired backup archive(s)."

log "=== Daily Database Backup Completed Successfully ==="
exit 0
