#!/bin/bash
# ============================================
# OpenCitiVibes Staging VPS Setup Script
# ============================================
# Run this on a fresh Ubuntu VPS with Docker installed
# Usage: bash setup-staging-vps.sh
# ============================================

set -e

DEPLOY_DIR="/home/ubuntu/opencitivibes"
DOMAIN="ideespourmontreal.opencitivibes.ovh"
CONTAINER_PREFIX="idees-mtl"

echo "=== OpenCitiVibes Staging Setup ==="
echo "Deploy directory: $DEPLOY_DIR"
echo "Domain: $DOMAIN"
echo ""

# Create directory structure
echo "[1/8] Creating directory structure..."
mkdir -p "$DEPLOY_DIR"/{nginx/conf.d,config,ntfy,ssl}
cd "$DEPLOY_DIR"

# Generate secret key
echo "[2/8] Generating secret key..."
SECRET_KEY=$(openssl rand -hex 32)

# Create .env file
echo "[3/8] Creating .env file..."
cat > .env << EOF
# ============================================
# OpenCitiVibes Staging - Montreal Instance
# Generated: $(date -Iseconds)
# ============================================

# Instance Identity
COMPOSE_PROJECT_NAME=idees-montreal
CONTAINER_PREFIX=${CONTAINER_PREFIX}
VOLUME_PREFIX=idees-mtl
NETWORK_NAME=idees-mtl-network

# Docker Registry & Images
REGISTRY=ghcr.io
IMAGE_REPOSITORY=opencitivibes/opencitivibes
IMAGE_TAG=latest

# URLs & Domains
DOMAIN=${DOMAIN}
NEXT_PUBLIC_SITE_URL=https://${DOMAIN}
NEXT_PUBLIC_API_URL=https://${DOMAIN}/api
NEXT_PUBLIC_INSTANCE_NAME=Idées pour Montréal

# CORS
CORS_ORIGINS=["https://${DOMAIN}"]

# Backend Configuration
SECRET_KEY=${SECRET_KEY}
DATABASE_URL=sqlite:///./data/idees_montreal.db
PLATFORM_CONFIG_PATH=./config/platform.config.json
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
LOG_LEVEL=INFO
ENVIRONMENT=staging

# Admin - CHANGE THIS PASSWORD!
ADMIN_EMAIL=admin@idees-montreal.ca
ADMIN_PASSWORD=ChangeThisPassword2024!

# Timezone
TZ=America/Montreal

# Ntfy Push Notifications
NTFY_BASE_URL=https://ntfy.${DOMAIN}
NTFY_INTERNAL_URL=http://ntfy:80
NTFY_TOPIC_PREFIX=idees-admin
NTFY_CACHE_DURATION=24h
NTFY_ENABLED=true
APP_URL=https://${DOMAIN}

# Monitoring (optional)
SENTRY_DSN=
NEXT_PUBLIC_SENTRY_DSN=
EOF

# Download docker-compose.yml from repo
echo "[4/8] Downloading docker-compose.yml..."
curl -sL -o docker-compose.yml https://raw.githubusercontent.com/opencitivibes/opencitivibes/main/docker-compose.yml

# Download nginx.conf
echo "[5/8] Setting up nginx configuration..."
curl -sL -o nginx/nginx.conf https://raw.githubusercontent.com/opencitivibes/opencitivibes/main/nginx/nginx.conf

# Create nginx default.conf (processed from template)
cat > nginx/conf.d/default.conf << 'NGINXEOF'
upstream backend {
    server idees-mtl-backend:8000;
    keepalive 32;
}

upstream frontend {
    server idees-mtl-frontend:3000;
    keepalive 32;
}

server {
    listen 80;
    listen [::]:80;
    server_name ideespourmontreal.opencitivibes.ovh;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name ideespourmontreal.opencitivibes.ovh;

    ssl_certificate /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;
    ssl_session_tickets off;

    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;

    location /api/ {
        limit_req zone=api_limit burst=20 nodelay;
        limit_conn conn_limit 20;
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection "";
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
    }

    location /api/auth/ {
        limit_req zone=login_limit burst=5 nodelay;
        limit_conn conn_limit 5;
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection "";
    }

    location /api/health {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        access_log off;
    }

    location /_next/static {
        proxy_pass http://frontend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_cache_valid 200 365d;
        add_header Cache-Control "public, max-age=31536000, immutable";
    }

    location /_next/image {
        proxy_pass http://frontend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_cache_valid 200 60d;
    }

    location / {
        proxy_pass http://frontend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        add_header Cache-Control "no-cache, no-store, must-revalidate";
    }

    location = /favicon.ico { proxy_pass http://frontend; access_log off; log_not_found off; }
    location = /robots.txt { proxy_pass http://frontend; access_log off; log_not_found off; }
    location = /sitemap.xml { proxy_pass http://frontend; access_log off; }
    location = /health { access_log off; return 200 "healthy\n"; add_header Content-Type text/plain; }
    location ~ /\. { deny all; access_log off; log_not_found off; }
}
NGINXEOF

# Create ntfy server.yml
echo "[6/8] Setting up ntfy configuration..."
cat > ntfy/server.yml << EOF
auth-file: "/var/lib/ntfy/user.db"
auth-default-access: "deny-all"
base-url: "https://ntfy.${DOMAIN}"
behind-proxy: true
cache-file: "/var/cache/ntfy/cache.db"
cache-duration: "24h"
attachment-cache-dir: "/var/cache/ntfy/attachments"
attachment-total-size-limit: "100M"
attachment-file-size-limit: "5M"
attachment-expiry-duration: "24h"
visitor-subscription-limit: 30
visitor-request-limit-burst: 60
visitor-request-limit-replenish: "5s"
enable-signup: false
enable-login: true
log-level: "info"
log-format: "json"
EOF

# Download platform config
echo "[7/8] Downloading platform configuration..."
curl -sL -o config/platform.config.json https://raw.githubusercontent.com/opencitivibes/opencitivibes/main/instances/montreal/platform.config.json

# SSL setup instructions
echo "[8/8] SSL Certificate Setup..."
echo ""
echo "=== MANUAL STEPS REQUIRED ==="
echo ""
echo "0. (Rootless Docker) Allow binding to privileged ports:"
echo "   echo 'net.ipv4.ip_unprivileged_port_start=80' | sudo tee -a /etc/sysctl.conf"
echo "   sudo sysctl -p"
echo ""
echo "1. Set up SSL certificates with certbot:"
echo "   sudo apt install certbot"
echo "   sudo certbot certonly --standalone -d ${DOMAIN}"
echo ""
echo "2. Copy certificates to deploy directory:"
echo "   sudo cp /etc/letsencrypt/live/${DOMAIN}/fullchain.pem ${DEPLOY_DIR}/ssl/"
echo "   sudo cp /etc/letsencrypt/live/${DOMAIN}/privkey.pem ${DEPLOY_DIR}/ssl/"
echo "   sudo chown ubuntu:ubuntu ${DEPLOY_DIR}/ssl/*"
echo ""
echo "3. Update docker-compose.yml to mount local SSL certs:"
echo "   Change: ssl_certs:/etc/nginx/ssl:ro"
echo "   To:     ./ssl:/etc/nginx/ssl:ro"
echo ""
echo "4. Login to GitHub Container Registry:"
echo "   echo \$GITHUB_TOKEN | docker login ghcr.io -u opencitivibes --password-stdin"
echo ""
echo "5. Pull and start containers:"
echo "   docker compose pull"
echo "   docker compose up -d"
echo ""
echo "=== Setup Complete ==="
echo ""
echo "Files created in ${DEPLOY_DIR}:"
ls -la "$DEPLOY_DIR"
echo ""
echo "IMPORTANT: Change the ADMIN_PASSWORD in .env before starting!"
echo ""
echo "=== TROUBLESHOOTING ==="
echo ""
echo "If backend shows 'table not found' errors after first start:"
echo "   docker exec ${CONTAINER_PREFIX}-backend alembic stamp head"
echo "   docker compose restart backend"
echo ""
echo "To view container logs:"
echo "   docker compose logs -f backend"
echo "   docker compose logs -f frontend"
echo "   docker compose logs -f nginx"
