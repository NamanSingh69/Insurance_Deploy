#!/usr/bin/env bash
# Run directly on the VPS after deployment. Credentials are read from the shell,
# never embedded in this repository.

set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

check_service() {
    local service_name=$1
    printf 'Checking %s service... ' "$service_name"
    if systemctl is-active --quiet "$service_name"; then
        printf '%b\n' "${GREEN}ACTIVE${NC}"
    else
        printf '%b\n' "${RED}INACTIVE/FAILED${NC}"
        sudo journalctl -u "$service_name" -n 10 --no-pager
        exit 1
    fi
}

printf '%b\n' "${YELLOW}=== Motor Survey deployment verification ===${NC}"
check_service postgresql
check_service redis-server
check_service nginx
check_service insurance
check_service insurance-worker

printf 'Verifying Nginx configuration syntax... '
if sudo nginx -t >/dev/null 2>&1; then
    printf '%b\n' "${GREEN}OK${NC}"
else
    printf '%b\n' "${RED}SYNTAX ERROR${NC}"
    sudo nginx -t
    exit 1
fi

if [[ -z "${PGPASSWORD:-}" ]]; then
    printf '%b\n' "${RED}PGPASSWORD is required for the database check. Export it from the protected production environment and retry.${NC}"
    exit 2
fi

DB_HOST="${DB_HOST:-127.0.0.1}"
DB_NAME="${DB_NAME:-insurance_db}"
DB_USER="${DB_USER:-insurance_user}"
printf 'Checking PostgreSQL connection and schema migrations... '
if PGPASSWORD="$PGPASSWORD" psql -X -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 \
    -c 'SELECT version, applied_at FROM schema_migrations ORDER BY version;' >/dev/null; then
    printf '%b\n' "${GREEN}CONNECTED${NC}"
    PGPASSWORD="$PGPASSWORD" psql -X -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" \
        -c 'SELECT version, applied_at FROM schema_migrations ORDER BY version;'
else
    printf '%b\n' "${RED}CONNECTION OR MIGRATION CHECK FAILED${NC}"
    exit 1
fi

printf 'Testing Gunicorn healthz endpoint... '
HEALTHZ_CODE="$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/healthz || true)"
if [[ "$HEALTHZ_CODE" == '200' ]]; then
    printf '%b\n' "${GREEN}OK (HTTP ${HEALTHZ_CODE})${NC}"
else
    printf '%b\n' "${RED}FAILED (HTTP ${HEALTHZ_CODE})${NC}"
    exit 1
fi

printf 'Testing Nginx local reverse proxy port 80... '
NGINX_CODE="$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1/login || true)"
if [[ "$NGINX_CODE" == '200' || "$NGINX_CODE" == '302' ]]; then
    printf '%b\n' "${GREEN}OK (HTTP ${NGINX_CODE})${NC}"
else
    printf '%b\n' "${RED}FAILED (HTTP ${NGINX_CODE})${NC}"
    exit 1
fi

printf '%b\n' "${GREEN}=== Verification complete: all checks passed. ===${NC}"
