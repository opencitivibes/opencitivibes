#!/bin/bash
# ============================================
# OpenCitiVibes Staging VPS Setup Script
# ============================================
# Run this on a fresh Ubuntu VPS with Docker installed
# Usage: bash setup-staging-vps.sh
# ============================================

set -e

# Configuration - customize these for your instance
DEPLOY_DIR="/home/ubuntu/opencitivibes"
DOMAIN="ideespourmontreal.opencitivibes.ovh"
CONTAINER_PREFIX="idees-mtl"
ADMIN_EMAIL="ideespourmontreal@opencitivibes.ovh"
INSTANCE_NAME="Idées pour Montréal"

echo "=== OpenCitiVibes Staging Setup ==="
echo "Deploy directory: $DEPLOY_DIR"
echo "Domain: $DOMAIN"
echo "Admin email: $ADMIN_EMAIL"
echo "Instance: $INSTANCE_NAME"
echo ""

# Create directory structure
echo "[1/9] Creating directory structure..."
mkdir -p "$DEPLOY_DIR"/{nginx/conf.d,config/images,backend/config,ntfy,ssl,instance-assets}
cd "$DEPLOY_DIR"

# Generate secret key
echo "[2/9] Generating secret key..."
SECRET_KEY=$(openssl rand -hex 32)

# Create .env file
echo "[3/9] Creating .env file..."
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
NEXT_PUBLIC_INSTANCE_NAME=${INSTANCE_NAME}

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

# Admin credentials (used on first startup to seed the database)
# IMPORTANT: Change the password before deploying!
ADMIN_EMAIL=${ADMIN_EMAIL}
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

# SMTP Email Configuration (OVH)
# Used for passwordless login magic links
EMAIL_PROVIDER=smtp
SMTP_HOST=smtp.mail.ovh.ca
SMTP_PORT=465
SMTP_USE_TLS=false
SMTP_USE_SSL=true
SMTP_USER=\${ADMIN_EMAIL}
SMTP_PASSWORD=CHANGE_ME_TO_EMAIL_PASSWORD
SMTP_FROM_EMAIL=\${ADMIN_EMAIL}
SMTP_FROM_NAME=\${INSTANCE_NAME}

# Monitoring (optional)
SENTRY_DSN=
NEXT_PUBLIC_SENTRY_DSN=
EOF

# Download docker-compose.yml from repo and patch for staging
echo "[4/9] Downloading and configuring docker-compose.yml..."
curl -sL -o docker-compose.yml https://raw.githubusercontent.com/opencitivibes/opencitivibes/main/docker-compose.yml

# Patch docker-compose.yml for staging:
# 1. Use local SSL certs instead of volume
sed -i 's|ssl_certs:/etc/nginx/ssl:ro|./ssl:/etc/nginx/ssl:ro|g' docker-compose.yml

# 2. Add HOSTNAME=0.0.0.0 for frontend health checks (Next.js standalone)
sed -i '/NEXT_PUBLIC_INSTANCE_NAME/a\      - HOSTNAME=0.0.0.0' docker-compose.yml

# 3. Add volume mount for instance assets (persists across container updates)
sed -i '/NEXT_PUBLIC_ENVIRONMENT/a\    volumes:\n      - ./instance-assets:/app/public/instance:ro' docker-compose.yml

# 4. Fix frontend health check to use 127.0.0.1 (wget resolves localhost to IPv6)
sed -i 's|http://localhost:3000/api/health|http://127.0.0.1:3000/api/health|g' docker-compose.yml

# Download nginx.conf
echo "[5/9] Setting up nginx configuration..."
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
echo "[6/9] Setting up ntfy configuration..."
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

# Download platform config and instance assets
echo "[7/9] Setting up platform configuration and instance assets..."

# NOTE: Instance config and assets are NOT stored in GitHub (contain branding/secrets)
# You must manually copy these files from a secure source or create them:
#
# Required files:
#   - backend/config/platform.config.json  (backend reads this)
#   - instance-assets/hero.png             (hero image)
#   - instance-assets/logo.svg             (logo)
#
# Create platform config with correct schema
cat > backend/config/platform.config.json << 'CONFIGEOF'
{
  "platform": {
    "name": "OpenCitiVibes",
    "version": "1.0.0"
  },
  "instance": {
    "id": "montreal",
    "name": {
      "en": "Ideas for Montreal",
      "fr": "Idées pour Montréal"
    },
    "entity": {
      "type": "city",
      "name": {
        "en": "Montreal",
        "fr": "Montréal"
      },
      "region": {
        "en": "Quebec",
        "fr": "Québec"
      },
      "country": {
        "en": "Canada",
        "fr": "Canada"
      }
    },
    "location": {
      "display": {
        "en": "Montreal, Quebec",
        "fr": "Montréal, Québec"
      },
      "coordinates": {
        "lat": 45.5017,
        "lng": -73.5673
      },
      "timezone": "America/Montreal"
    }
  },
  "database": {
    "file": "idees_montreal.db"
  },
  "contact": {
    "email": "contact@idees-montreal.ca",
    "support_email": "support@idees-montreal.ca"
  },
  "legal": {
    "jurisdiction": {
      "en": "Quebec and Canada",
      "fr": "Québec et Canada"
    },
    "courts": {
      "en": "competent courts of Quebec",
      "fr": "tribunaux compétents du Québec"
    },
    "privacy_authority": {
      "name": {
        "en": "Commission d'accès à l'information du Québec",
        "fr": "Commission d'accès à l'information du Québec"
      },
      "acronym": "CAI",
      "url": "https://www.cai.gouv.qc.ca"
    }
  },
  "branding": {
    "primary_color": "#9333ea",
    "secondary_color": "#6b21a8",
    "hero_image": "/instance/hero.png",
    "logo": "/instance/logo.svg"
  },
  "features": {
    "voting_enabled": true,
    "comments_enabled": true,
    "tags_enabled": true,
    "quality_feedback_enabled": true,
    "moderation_enabled": true,
    "analytics_public": false
  },
  "localization": {
    "default_locale": "fr",
    "supported_locales": ["fr", "en"],
    "date_format": {
      "fr": "DD/MM/YYYY",
      "en": "MM/DD/YYYY"
    }
  }
}
CONFIGEOF

echo "  - Created default platform.config.json (customize as needed)"

# Create placeholder instance assets (replace with actual branding)
echo "  - Instance assets directory: $DEPLOY_DIR/instance-assets/"
echo "  - Upload your hero.png and logo.svg to this directory"

# Create helper script for copying instance assets into frontend container
echo "[8/9] Creating asset deployment script..."
cat > deploy-instance-assets.sh << 'ASSETSCRIPT'
#!/bin/bash
# Deploy instance assets to frontend container
# Run this after 'docker compose up -d'

CONTAINER_PREFIX="${CONTAINER_PREFIX:-idees-mtl}"
ASSETS_DIR="./instance-assets"

if [ ! -d "$ASSETS_DIR" ] || [ -z "$(ls -A $ASSETS_DIR 2>/dev/null)" ]; then
    echo "Warning: No instance assets found in $ASSETS_DIR"
    echo "Upload hero.png and logo.svg to this directory first"
    exit 1
fi

echo "Deploying instance assets to frontend container..."

# Create directories in frontend container
docker exec -u root ${CONTAINER_PREFIX}-frontend mkdir -p /app/public/instance
docker exec -u root ${CONTAINER_PREFIX}-frontend mkdir -p /app/public/static/images

# Copy instance assets (hero, logo)
for file in "$ASSETS_DIR"/*; do
    if [ -f "$file" ]; then
        filename=$(basename "$file")
        echo "  - Copying $filename to /app/public/instance/"
        docker cp "$file" ${CONTAINER_PREFIX}-frontend:/app/public/instance/
    fi
done

# Copy logo to static/images as well (fallback location)
if [ -f "$ASSETS_DIR/logo.svg" ]; then
    docker cp "$ASSETS_DIR/logo.svg" ${CONTAINER_PREFIX}-frontend:/app/public/static/images/logo_tr3.svg
fi

# Restart frontend to pick up new files
echo "Restarting frontend container..."
docker compose restart frontend

echo "Instance assets deployed successfully!"
ASSETSCRIPT
chmod +x deploy-instance-assets.sh
echo "  - Created deploy-instance-assets.sh"

# Create admin seeding script
echo "[9/10] Creating admin seeding script..."
cat > seed-admin.sh << 'SEEDSCRIPT'
#!/bin/bash
# Initialize database and seed admin user
# Run this after containers are up

CONTAINER_PREFIX="${CONTAINER_PREFIX:-idees-mtl}"

# Read from .env file if not set
if [ -z "$ADMIN_EMAIL" ]; then
    ADMIN_EMAIL=$(grep '^ADMIN_EMAIL=' .env | cut -d'=' -f2)
fi
if [ -z "$ADMIN_PASSWORD" ]; then
    ADMIN_PASSWORD=$(grep '^ADMIN_PASSWORD=' .env | cut -d'=' -f2)
fi

if [ -z "$ADMIN_EMAIL" ] || [ -z "$ADMIN_PASSWORD" ]; then
    echo "Error: ADMIN_EMAIL and ADMIN_PASSWORD must be set in .env"
    exit 1
fi

# Run database migrations first
echo "Running database migrations..."
docker exec ${CONTAINER_PREFIX}-backend alembic upgrade head 2>/dev/null || {
    echo "Migration failed, stamping head and retrying..."
    docker exec ${CONTAINER_PREFIX}-backend alembic stamp head
}

echo "Creating admin user: $ADMIN_EMAIL"

docker exec ${CONTAINER_PREFIX}-backend python3 -c "
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from repositories.db_models import User
from authentication.auth import get_password_hash
import os

engine = create_engine('sqlite:///./data/idees_montreal.db')
Session = sessionmaker(bind=engine)
session = Session()

# Check if user already exists
existing = session.query(User).filter_by(email='$ADMIN_EMAIL').first()
if existing:
    print(f'Admin user already exists: $ADMIN_EMAIL')
    session.close()
    exit(0)

# Create admin user
admin = User(
    email='$ADMIN_EMAIL',
    username='$ADMIN_EMAIL'.split('@')[0],
    hashed_password=get_password_hash('$ADMIN_PASSWORD'),
    display_name='Admin',
    is_active=True,
    is_global_admin=True
)
session.add(admin)
session.commit()
print(f'Created admin user: $ADMIN_EMAIL')
session.close()
"

echo "Admin seeding complete!"

# Configure ntfy anonymous write access for backend
echo "Configuring ntfy topic permissions..."
TOPIC_PREFIX=\$(grep '^NTFY_TOPIC_PREFIX=' .env | cut -d'=' -f2)
TOPIC_PREFIX=\${TOPIC_PREFIX:-admin}
docker exec \${CONTAINER_PREFIX}-ntfy ntfy access '*' "\${TOPIC_PREFIX}-*" write 2>/dev/null || {
    echo "Warning: Could not configure ntfy permissions (container may not be ready)"
}
echo "Ntfy configuration complete!"
SEEDSCRIPT
chmod +x seed-admin.sh
echo "  - Created seed-admin.sh"

# SSL setup instructions
echo "[10/10] SSL Certificate Setup..."
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
echo "5. Upload instance assets to instance-assets/ directory:"
echo "   scp hero.png logo.svg ubuntu@\${DOMAIN}:${DEPLOY_DIR}/instance-assets/"
echo ""
echo "6. Pull and start containers:"
echo "   docker compose pull"
echo "   docker compose up -d"
echo ""
echo "7. Deploy instance assets to frontend container:"
echo "   ./deploy-instance-assets.sh"
echo ""
echo "8. Seed the admin user:"
echo "   ./seed-admin.sh"
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
