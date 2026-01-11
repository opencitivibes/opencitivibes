#!/bin/bash
# ============================================
# OpenCitiVibes Production VPS Setup Script
# ============================================
# Run this on a fresh Ubuntu VPS with Docker installed
# Usage: bash setup-production-vps.sh
#
# Differences from staging:
# - Uses PostgreSQL instead of SQLite
# - Uses the 'prod' Docker profile
# - ENVIRONMENT=production
#
# ⚠️  WARNING: FOR FRESH VPS ONLY!
# This script OVERWRITES configuration files:
#   - .env (secrets, database passwords)
#   - docker-compose.yml
#   - nginx configs
#   - ntfy/server.yml
#   - platform.config.json
#
# DO NOT run on existing deployments - you will lose configuration!
# For updates, use deploy.sh or manually update specific files.
# ============================================

set -e

# Configuration - CUSTOMIZE THESE FOR YOUR INSTANCE
# ================================================
DEPLOY_DIR="/home/ubuntu/opencitivibes"
DOMAIN="${DOMAIN:-your-domain.example.com}"           # Set via: DOMAIN=example.com bash setup-production-vps.sh
CONTAINER_PREFIX="${CONTAINER_PREFIX:-your-prefix}"   # Container naming prefix
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@example.com}"       # Admin email address
INSTANCE_NAME="${INSTANCE_NAME:-Your Instance Name}"  # Display name for the instance

echo "=== OpenCitiVibes Production Setup ==="
echo "Deploy directory: $DEPLOY_DIR"
echo "Domain: $DOMAIN"
echo "Admin email: $ADMIN_EMAIL"
echo "Instance: $INSTANCE_NAME"
echo "Database: PostgreSQL"
echo ""

# Create directory structure
echo "[1/10] Creating directory structure..."
mkdir -p "$DEPLOY_DIR"/{nginx/conf.d,config/images,backend/config,ntfy,ssl,instance-assets}
cd "$DEPLOY_DIR"

# Generate secrets
echo "[2/10] Generating secrets..."
SECRET_KEY=$(openssl rand -hex 32)
TOTP_ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
POSTGRES_PASSWORD=$(openssl rand -hex 24)
ADMIN_PASSWORD=$(openssl rand -base64 24 | tr -d '/+=' | head -c 24)

# Create .env file
echo "[3/10] Creating .env file..."
cat > .env << EOF
# ============================================
# OpenCitiVibes Production - Montreal Instance
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
TOTP_ENCRYPTION_KEY=${TOTP_ENCRYPTION_KEY}
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
LOG_LEVEL=INFO
ENVIRONMENT=production

# PostgreSQL Database (prod profile)
DATABASE_URL=postgresql://opencitivibes:${POSTGRES_PASSWORD}@postgres:5432/opencitivibes
POSTGRES_USER=opencitivibes
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
POSTGRES_DB=opencitivibes

# Platform config path
PLATFORM_CONFIG_PATH=./config/platform.config.json

# Admin credentials (used on first startup to seed the database)
# Password is auto-generated - save it securely!
ADMIN_EMAIL=${ADMIN_EMAIL}
ADMIN_PASSWORD=${ADMIN_PASSWORD}

# Timezone
TZ=America/Montreal

# Ntfy Push Notifications
NTFY_BASE_URL=https://ntfy.${DOMAIN}
NTFY_INTERNAL_URL=http://ntfy:80
NTFY_TOPIC_PREFIX=idees-admin
NTFY_CACHE_DURATION=24h
NTFY_ENABLED=true
APP_URL=https://${DOMAIN}

# Ntfy admin user for mobile app subscriptions (auto-generated if not set)
# NTFY_ADMIN_PASSWORD=YourSecurePassword

# SMTP Email Configuration (Postfix container)
# Used for passwordless login magic links
EMAIL_PROVIDER=smtp
SMTP_HOST=postfix
SMTP_PORT=25
SMTP_USE_TLS=false
SMTP_USE_SSL=false
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=${ADMIN_EMAIL}
SMTP_FROM_NAME=${INSTANCE_NAME}

# Mail domain for Postfix DKIM signing
MAIL_DOMAIN=opencitivibes.ovh

# Monitoring - Sentry error tracking (optional - get DSN from sentry.io)
# SENTRY_DSN=https://your-sentry-dsn@sentry.io/project
# NEXT_PUBLIC_SENTRY_DSN=https://your-sentry-dsn@sentry.io/project
EOF

echo ""
echo "============================================"
echo "GENERATED CREDENTIALS (save these!):"
echo "  Admin Email: ${ADMIN_EMAIL}"
echo "  Admin Password: ${ADMIN_PASSWORD}"
echo "  PostgreSQL Password: ${POSTGRES_PASSWORD:0:8}... (full in .env)"
echo "============================================"
echo ""

# Download docker-compose.yml from repo and patch for production
echo "[4/10] Downloading and configuring docker-compose.yml..."
curl -sL -o docker-compose.yml https://raw.githubusercontent.com/opencitivibes/opencitivibes/main/docker-compose.yml

# Patch docker-compose.yml for production:
# 1. Use local SSL certs instead of volume
sed -i 's|ssl_certs:/etc/nginx/ssl:ro|./ssl:/etc/nginx/ssl:ro|g' docker-compose.yml

# 2. Add HOSTNAME=0.0.0.0 for frontend health checks (Next.js standalone)
sed -i '/NEXT_PUBLIC_INSTANCE_NAME/a\      - HOSTNAME=0.0.0.0' docker-compose.yml

# 3. Fix frontend health check to use 127.0.0.1 (wget resolves localhost to IPv6)
sed -i 's|http://localhost:3000/api/health|http://127.0.0.1:3000/api/health|g' docker-compose.yml

# Download nginx configuration files from repo
echo "[5/10] Setting up nginx configuration from templates..."
curl -sL -o nginx/nginx.conf https://raw.githubusercontent.com/opencitivibes/opencitivibes/main/nginx/nginx.conf

# Download templates and process them with envsubst
curl -sL -o /tmp/default.conf.template https://raw.githubusercontent.com/opencitivibes/opencitivibes/main/nginx/conf.d/default.conf.template
curl -sL -o /tmp/ntfy.conf.template https://raw.githubusercontent.com/opencitivibes/opencitivibes/main/nginx/conf.d/ntfy.conf.template

# Generate configs from templates
export DOMAIN CONTAINER_PREFIX
envsubst '${DOMAIN} ${CONTAINER_PREFIX}' < /tmp/default.conf.template > nginx/conf.d/default.conf
envsubst '${DOMAIN} ${CONTAINER_PREFIX}' < /tmp/ntfy.conf.template > nginx/conf.d/ntfy.conf

echo "  - Generated nginx/conf.d/default.conf from template"
echo "  - Generated nginx/conf.d/ntfy.conf from template (secured - web UI blocked)"

# Cleanup temp files
rm -f /tmp/default.conf.template /tmp/ntfy.conf.template

# Create ntfy server.yml
echo "[6/10] Setting up ntfy configuration..."
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
echo "[7/10] Setting up platform configuration and instance assets..."

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
    "type": "postgresql"
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
echo ""
echo "  NOTE: Legal documents and instance assets must be uploaded from your local"
echo "  instances/ directory BEFORE starting containers. See step 4 below."
echo ""
echo "  - Instance assets directory: $DEPLOY_DIR/instance-assets/"
echo "  - Legal documents directory: $DEPLOY_DIR/backend/config/legal/"

# Create admin seeding script for PostgreSQL
echo "[8/10] Creating admin seeding script (PostgreSQL)..."
cat > seed-admin.sh << 'SEEDSCRIPT'
#!/bin/bash
# Initialize database and seed admin user (PostgreSQL version)
# Run this after containers are up

CONTAINER_PREFIX="${CONTAINER_PREFIX:-idees-mtl}"

# Read from .env file if not set
if [ -z "$ADMIN_EMAIL" ]; then
    ADMIN_EMAIL=$(grep '^ADMIN_EMAIL=' .env | cut -d'=' -f2)
fi
if [ -z "$ADMIN_PASSWORD" ]; then
    ADMIN_PASSWORD=$(grep '^ADMIN_PASSWORD=' .env | cut -d'=' -f2)
fi
if [ -z "$DATABASE_URL" ]; then
    DATABASE_URL=$(grep '^DATABASE_URL=' .env | cut -d'=' -f2-)
fi

if [ -z "$ADMIN_EMAIL" ] || [ -z "$ADMIN_PASSWORD" ]; then
    echo "Error: ADMIN_EMAIL and ADMIN_PASSWORD must be set in .env"
    exit 1
fi

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
for i in {1..30}; do
    if docker exec ${CONTAINER_PREFIX}-postgres pg_isready -U opencitivibes -d opencitivibes >/dev/null 2>&1; then
        echo "PostgreSQL is ready!"
        break
    fi
    echo "  Waiting... ($i/30)"
    sleep 2
done

# Run database migrations
echo "Running database migrations..."
docker exec ${CONTAINER_PREFIX}-backend alembic upgrade head 2>/dev/null || {
    echo "Migration failed, stamping head and retrying..."
    docker exec ${CONTAINER_PREFIX}-backend alembic stamp head
    docker exec ${CONTAINER_PREFIX}-backend alembic upgrade head
}

echo "Creating admin user: $ADMIN_EMAIL"

docker exec ${CONTAINER_PREFIX}-backend python3 -c "
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from repositories.db_models import User
from authentication.auth import get_password_hash
import os

db_url = os.environ.get('DATABASE_URL', '$DATABASE_URL')
engine = create_engine(db_url)
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
TOPIC_PREFIX=$(grep '^NTFY_TOPIC_PREFIX=' .env | cut -d'=' -f2)
TOPIC_PREFIX=${TOPIC_PREFIX:-admin}
docker exec ${CONTAINER_PREFIX}-ntfy ntfy access '*' "${TOPIC_PREFIX}-*" write 2>/dev/null || {
    echo "Warning: Could not configure ntfy permissions (container may not be ready)"
}

# Create ntfy admin user for mobile app subscriptions
echo "Creating ntfy admin user..."
NTFY_ADMIN_PASS=$(grep '^NTFY_ADMIN_PASSWORD=' .env | cut -d'=' -f2)
NTFY_ADMIN_PASS=${NTFY_ADMIN_PASS:-$(openssl rand -base64 12 | tr -d '/+=')}
docker exec -e NTFY_PASSWORD="${NTFY_ADMIN_PASS}" ${CONTAINER_PREFIX}-ntfy ntfy user add --role=admin --ignore-exists admin 2>/dev/null || {
    echo "Warning: Could not create ntfy admin user (container may not be ready)"
}
# Create auth token for backend to read notification history
echo "Creating ntfy auth token for backend..."
NTFY_TOKEN=$(docker exec ${CONTAINER_PREFIX}-ntfy ntfy token add --label=backend admin 2>/dev/null | grep -oP 'token \K[^ ]+')
if [ -n "$NTFY_TOKEN" ]; then
    # Add token to .env if not already present
    grep -q "^NTFY_AUTH_TOKEN=" .env || echo "NTFY_AUTH_TOKEN=${NTFY_TOKEN}" >> .env
    # Update .env with new token
    sed -i "s/^NTFY_AUTH_TOKEN=.*/NTFY_AUTH_TOKEN=${NTFY_TOKEN}/" .env
    echo "  - Token created and added to .env"
    echo "  - Restart backend to apply: docker compose --profile prod up -d backend"
fi

echo ""
echo "============================================"
echo "NTFY ADMIN CREDENTIALS (save these!):"
echo "  Server: https://ntfy.\${DOMAIN}"
echo "  Username: admin"
echo "  Password: ${NTFY_ADMIN_PASS}"
echo "============================================"
echo ""
echo "Ntfy configuration complete!"
SEEDSCRIPT
chmod +x seed-admin.sh
echo "  - Created seed-admin.sh"

# Create backup script for PostgreSQL
echo "[9/10] Creating backup script (PostgreSQL)..."
mkdir -p scripts
cat > scripts/backup.sh << 'BACKUPSCRIPT'
#!/bin/bash
# Backup PostgreSQL database and instance assets
# Run periodically via cron or before deployments

CONTAINER_PREFIX="${CONTAINER_PREFIX:-idees-mtl}"
BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

echo "Creating PostgreSQL backup..."
docker exec ${CONTAINER_PREFIX}-postgres pg_dump -U opencitivibes -d opencitivibes > "$BACKUP_DIR/db_${TIMESTAMP}.sql"

echo "Backing up instance assets..."
tar -czf "$BACKUP_DIR/assets_${TIMESTAMP}.tar.gz" instance-assets/ backend/config/ .env

echo "Cleaning up old backups (keeping last 7 days)..."
find "$BACKUP_DIR" -type f -mtime +7 -delete

echo "Backup complete: $BACKUP_DIR"
ls -lh "$BACKUP_DIR"
BACKUPSCRIPT
mkdir -p scripts
chmod +x scripts/backup.sh
echo "  - Created scripts/backup.sh"

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
echo "3. Login to GitHub Container Registry:"
echo "   echo \$GITHUB_TOKEN | docker login ghcr.io -u opencitivibes --password-stdin"
echo ""
echo "4. Upload instance files BEFORE starting containers:"
echo "   # From your local machine, in the project directory:"
echo "   scp -r instances/montreal/images/* ubuntu@${DOMAIN}:${DEPLOY_DIR}/instance-assets/"
echo "   scp -r instances/montreal/legal ubuntu@${DOMAIN}:${DEPLOY_DIR}/backend/config/"
echo "   scp instances/montreal/platform.config.json ubuntu@${DOMAIN}:${DEPLOY_DIR}/backend/config/"
echo ""
echo "5. Pull and start containers with PRODUCTION profile:"
echo "   docker compose --profile prod pull"
echo "   docker compose --profile prod up -d"
echo ""
echo "6. Seed the admin user:"
echo "   ./seed-admin.sh"
echo ""
echo "7. Configure DNS for email delivery:"
echo "   After containers start, get DKIM key:"
echo "   docker exec ${CONTAINER_PREFIX}-postfix cat /etc/opendkim/keys/opencitivibes.ovh/mail.txt"
echo ""
echo "   Add these DNS records to your domain (opencitivibes.ovh):"
echo "   "
echo "   SPF (TXT record for @):"
echo "   v=spf1 ip4:YOUR_VPS_IP ~all"
echo "   "
echo "   DKIM (TXT record for mail._domainkey):"
echo "   Copy the p= value from the DKIM key above"
echo "   "
echo "   DMARC (TXT record for _dmarc):"
echo "   v=DMARC1; p=quarantine; rua=mailto:${ADMIN_EMAIL}"
echo ""
echo "8. Open firewall ports for SMTP:"
echo "    sudo ufw allow 25/tcp comment 'SMTP'"
echo "    sudo ufw allow 587/tcp comment 'SMTP Submission'"
echo ""
echo "=== Setup Complete ==="
echo ""
echo "Files created in ${DEPLOY_DIR}:"
ls -la "$DEPLOY_DIR"
echo ""
echo "IMPORTANT:"
echo "  - Change the ADMIN_PASSWORD in .env before starting!"
echo "  - PostgreSQL password is auto-generated in .env"
echo "  - Use 'docker compose --profile prod' for all commands"
echo ""
echo "=== TROUBLESHOOTING ==="
echo ""
echo "If backend shows database connection errors:"
echo "   docker compose --profile prod logs postgres"
echo "   docker compose --profile prod restart backend"
echo ""
echo "To view container logs:"
echo "   docker compose --profile prod logs -f backend"
echo "   docker compose --profile prod logs -f frontend"
echo "   docker compose --profile prod logs -f postgres"
echo "   docker compose --profile prod logs -f nginx"
echo ""
