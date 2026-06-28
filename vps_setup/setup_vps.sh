#!/bin/bash
# setup_vps.sh - Initialization script for Ubuntu 24.04 VPS

set -e

echo "=== Updating packages ==="
sudo apt update && sudo apt upgrade -y

echo "=== Installing system dependencies ==="
sudo apt install -y python3-pip python3-venv python3-dev postgresql postgresql-contrib nginx certbot python3-certbot-nginx git

echo "=== Configuring PostgreSQL ==="
# Start and enable Postgres
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database and user (modify passwords as needed)
sudo -u postgres psql -c "CREATE USER insurance_user WITH PASSWORD 'surveyorportal@2026';" || true
sudo -u postgres psql -c "CREATE DATABASE insurance_db OWNER insurance_user;" || true
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE insurance_db TO insurance_user;" || true

echo "=== Creating App Directories ==="
sudo mkdir -p /var/www/insurance-app
sudo chown -R $USER:$USER /var/www/insurance-app

echo "=== Setup complete! ==="
echo "Next steps:"
echo "1. Upload your code files to /var/www/insurance-app"
echo "2. Inside /var/www/insurance-app, run:"
echo "   python3 -m venv venv"
echo "   source venv/bin/activate"
echo "   pip install -r requirements.txt"
echo "3. Create your .env file in /var/www/insurance-app with:"
echo "   DATABASE_URL=\"postgresql://insurance_user:surveyorportal@2026@localhost/insurance_db\""
echo "   GEMINI_API_KEY=\"...\""
echo "   GOOGLE_SHEETS_CREDENTIALS='...'"
echo "4. Copy the service file:"
echo "   sudo cp vps_setup/insurance.service /etc/systemd/system/insurance.service"
echo "   sudo systemctl daemon-reload"
echo "   sudo systemctl start insurance"
echo "   sudo systemctl enable insurance"
echo "5. Copy the Nginx config:"
echo "   sudo cp vps_setup/nginx.conf /etc/nginx/sites-available/insurance"
echo "   sudo ln -sf /etc/nginx/sites-available/insurance /etc/nginx/sites-enabled/"
echo "   sudo rm -f /etc/nginx/sites-enabled/default"
echo "   sudo systemctl restart nginx"
