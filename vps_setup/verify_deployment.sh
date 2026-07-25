#!/bin/bash
# verify_deployment.sh - VPS Deployment Verification Script
# To be executed directly on the Hostinger VPS.

set -e

# ANSI Color Codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Starting Hostinger VPS Deployment Verification ===${NC}"

# Helper function to check service status
check_service() {
    local service_name=$1
    echo -n "Checking $service_name service... "
    if systemctl is-active --quiet "$service_name"; then
        echo -e "${GREEN}ACTIVE${NC}"
    else
        echo -e "${RED}INACTIVE/FAILED${NC}"
        echo -e "${YELLOW}Last 10 logs for $service_name:${NC}"
        sudo journalctl -u "$service_name" -n 10 --no-pager
        exit 1
    fi
}

# 1. Check Essential Services
check_service "postgresql"
check_service "nginx"
check_service "insurance"
check_service "insurance-worker"

# 2. Verify Nginx Configuration
echo -n "Verifying Nginx configuration syntax... "
if sudo nginx -t &>/dev/null; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}SYNTAX ERROR${NC}"
    sudo nginx -t
    exit 1
fi

# 3. Verify PostgreSQL Connection and Schema Migrations
echo -n "Checking PostgreSQL local connection and schema migrations... "
if sudo PGPASSWORD='surveyorportal@2026' psql -U insurance_user -d insurance_db -h 127.0.0.1 -c "SELECT version_id, dirty FROM schema_migrations ORDER BY version_id DESC LIMIT 1;" &>/dev/null; then
    echo -e "${GREEN}CONNECTED${NC}"
    # Print migration status
    sudo PGPASSWORD='surveyorportal@2026' psql -U insurance_user -d insurance_db -h 127.0.0.1 -c "SELECT version_id, dirty FROM schema_migrations;"
else
    echo -e "${RED}CONNECTION FAILED${NC}"
    exit 1
fi

# 4. Verify Local App HTTP Bindings (Gunicorn)
echo -n "Testing Gunicorn local HTTP port 8000... "
GUNICORN_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/login || echo "000")
if [ "$GUNICORN_CODE" -eq 200 ] || [ "$GUNICORN_CODE" -eq 302 ]; then
    echo -e "${GREEN}OK (HTTP $GUNICORN_CODE)${NC}"
else
    echo -e "${RED}FAILED (HTTP $GUNICORN_CODE)${NC}"
    exit 1
fi

# 5. Verify Nginx HTTP Reverse Proxy Binding
echo -n "Testing Nginx local reverse proxy port 80... "
NGINX_CODE=$(curl -s -o /dev/null -w "%{http_code}" -H "Host: skinsurance.tech" http://127.0.0.1/login || echo "000")
if [ "$NGINX_CODE" -eq 200 ] || [ "$NGINX_CODE" -eq 302 ]; then
    echo -e "${GREEN}OK (HTTP $NGINX_CODE)${NC}"
else
    echo -e "${RED}FAILED (HTTP $NGINX_CODE)${NC}"
    exit 1
fi

echo -e "\n${GREEN}=== Verification Complete! All systems operational. ===${NC}"
