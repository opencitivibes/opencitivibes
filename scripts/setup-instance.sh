#!/bin/bash
# OpenCitiVibes Instance Setup Script
# Creates a new instance deployment with custom configuration
# Usage: ./scripts/setup-instance.sh <instance-name> <domain>

set -euo pipefail

# ============================================
# Colors
# ============================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log() { echo -e "${GREEN}[$(date +'%H:%M:%S')]${NC} $1"; }
warn() { echo -e "${YELLOW}[$(date +'%H:%M:%S')] WARNING:${NC} $1"; }
error() { echo -e "${RED}[$(date +'%H:%M:%S')] ERROR:${NC} $1" >&2; }
info() { echo -e "${BLUE}[$(date +'%H:%M:%S')] INFO:${NC} $1"; }

# ============================================
# Help
# ============================================
usage() {
    cat << EOF
OpenCitiVibes Instance Setup Script

Usage: $0 <instance-name> <domain> [OPTIONS]

Creates a new OpenCitiVibes instance deployment with custom configuration.

Arguments:
    instance-name    Short name for the instance (e.g., montreal, paris, toronto)
    domain          Domain name for the instance (e.g., ideas-montreal.ca)

Options:
    --base-path PATH    Base installation path (default: /opt/opencitivibes)
    --locale LOCALE     Default locale: en or fr (default: en)
    --entity-type TYPE  Entity type: city, region, organization (default: city)
    --skip-ssl          Skip SSL certificate setup
    -h, --help          Show this help message

Examples:
    $0 montreal ideas-montreal.ca
    $0 paris idees-paris.fr --locale fr
    $0 toronto ideas-toronto.ca --entity-type city

This script will:
    1. Create deployment directory structure
    2. Generate .env with instance-specific configuration
    3. Create platform.config.json
    4. Copy necessary files
    5. Provide next steps for deployment
EOF
    exit 1
}

# ============================================
# Parse Arguments
# ============================================
[[ $# -lt 2 ]] && usage

INSTANCE_NAME="$1"
DOMAIN="$2"
shift 2

# Defaults
BASE_PATH="/opt/opencitivibes"
DEFAULT_LOCALE="en"
ENTITY_TYPE="city"
SKIP_SSL=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --base-path)
            BASE_PATH="$2"
            shift 2
            ;;
        --locale)
            DEFAULT_LOCALE="$2"
            shift 2
            ;;
        --entity-type)
            ENTITY_TYPE="$2"
            shift 2
            ;;
        --skip-ssl)
            SKIP_SSL=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            error "Unknown option: $1"
            usage
            ;;
    esac
done

# Validate locale
if [[ "$DEFAULT_LOCALE" != "en" && "$DEFAULT_LOCALE" != "fr" ]]; then
    error "Locale must be 'en' or 'fr'"
    exit 1
fi

# Computed values
DEPLOY_PATH="${BASE_PATH}-${INSTANCE_NAME}"
SECRET_KEY=$(openssl rand -hex 32)
CONTAINER_PREFIX="ocv-${INSTANCE_NAME}"

# Capitalize instance name for display
INSTANCE_DISPLAY=$(echo "$INSTANCE_NAME" | sed 's/\b\(.\)/\u\1/g')

# ============================================
# Banner
# ============================================
echo ""
echo -e "${CYAN}╔════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                                                                    ║${NC}"
echo -e "${CYAN}║              ${NC}${GREEN}OpenCitiVibes Instance Setup${NC}${CYAN}                         ║${NC}"
echo -e "${CYAN}║                                                                    ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  Instance:     ${GREEN}$INSTANCE_NAME${NC}"
echo -e "  Domain:       ${GREEN}$DOMAIN${NC}"
echo -e "  Deploy Path:  ${GREEN}$DEPLOY_PATH${NC}"
echo -e "  Locale:       ${GREEN}$DEFAULT_LOCALE${NC}"
echo -e "  Entity Type:  ${GREEN}$ENTITY_TYPE${NC}"
echo ""

# ============================================
# Confirmation
# ============================================
read -p "Proceed with setup? (y/N): " confirm
if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    echo "Aborted"
    exit 0
fi

echo ""

# ============================================
# Create Directory Structure
# ============================================
log "Creating deployment directories..."

mkdir -p "$DEPLOY_PATH"/{backend/config,nginx/conf.d,ssl,backups,logs}

# ============================================
# Create .env File
# ============================================
log "Creating .env configuration..."

cat > "$DEPLOY_PATH/.env" << EOF
# ============================================
# OpenCitiVibes Instance: $INSTANCE_NAME
# Generated: $(date)
# ============================================

# Instance Identity
COMPOSE_PROJECT_NAME=ocv-${INSTANCE_NAME}
CONTAINER_PREFIX=${CONTAINER_PREFIX}
VOLUME_PREFIX=ocv-${INSTANCE_NAME}
NETWORK_NAME=ocv-${INSTANCE_NAME}-network

# Docker Registry
REGISTRY=ghcr.io
IMAGE_REPOSITORY=your-org/opencitivibes
IMAGE_TAG=latest

# URLs
DOMAIN=$DOMAIN
NEXT_PUBLIC_SITE_URL=https://$DOMAIN
NEXT_PUBLIC_API_URL=https://$DOMAIN/api
CORS_ORIGINS=["https://$DOMAIN"]

# Security (GENERATED - keep secret!)
SECRET_KEY=$SECRET_KEY
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
ENVIRONMENT=production

# Admin (CHANGE THESE!)
ADMIN_EMAIL=admin@$DOMAIN
ADMIN_PASSWORD=ChangeMe!2024

# Database
DATABASE_URL=sqlite:///./data/opencitivibes.db
PLATFORM_CONFIG_PATH=./config/platform.config.json

# Frontend
NEXT_PUBLIC_INSTANCE_NAME=Ideas for $INSTANCE_DISPLAY
NEXT_PUBLIC_DEFAULT_LOCALE=$DEFAULT_LOCALE
NEXT_PUBLIC_ENVIRONMENT=production

# Logging
LOG_LEVEL=INFO

# Monitoring (Optional)
SENTRY_DSN=
NEXT_PUBLIC_SENTRY_DSN=

# SSL
SSL_EMAIL=admin@$DOMAIN
EOF

# ============================================
# Create Platform Config
# ============================================
log "Creating platform configuration..."

# Generate entity names based on locale
if [[ "$DEFAULT_LOCALE" == "fr" ]]; then
    ENTITY_NAME_EN="$INSTANCE_DISPLAY"
    ENTITY_NAME_FR="$INSTANCE_DISPLAY"
    PLATFORM_NAME_EN="Ideas for $INSTANCE_DISPLAY"
    PLATFORM_NAME_FR="Idées pour $INSTANCE_DISPLAY"
else
    ENTITY_NAME_EN="$INSTANCE_DISPLAY"
    ENTITY_NAME_FR="$INSTANCE_DISPLAY"
    PLATFORM_NAME_EN="Ideas for $INSTANCE_DISPLAY"
    PLATFORM_NAME_FR="Idées pour $INSTANCE_DISPLAY"
fi

cat > "$DEPLOY_PATH/backend/config/platform.config.json" << EOF
{
  "platform": {
    "name": "OpenCitiVibes",
    "version": "1.0.0"
  },
  "instance": {
    "name": {
      "en": "$PLATFORM_NAME_EN",
      "fr": "$PLATFORM_NAME_FR"
    },
    "tagline": {
      "en": "Share your ideas for a better $INSTANCE_DISPLAY",
      "fr": "Partagez vos idées pour un meilleur $INSTANCE_DISPLAY"
    },
    "entity": {
      "type": "$ENTITY_TYPE",
      "name": {
        "en": "$ENTITY_NAME_EN",
        "fr": "$ENTITY_NAME_FR"
      }
    },
    "location": {
      "display": {
        "en": "$INSTANCE_DISPLAY",
        "fr": "$INSTANCE_DISPLAY"
      }
    }
  },
  "contact": {
    "email": "contact@$DOMAIN"
  },
  "localization": {
    "default_locale": "$DEFAULT_LOCALE",
    "supported_locales": ["en", "fr"]
  },
  "features": {
    "voting": true,
    "comments": true,
    "user_submissions": true,
    "official_responses": true,
    "quality_voting": true
  }
}
EOF

# ============================================
# Create Legal Config (Template)
# ============================================
log "Creating legal configuration template..."

cat > "$DEPLOY_PATH/backend/config/legal.config.json" << EOF
{
  "terms_of_service": {
    "effective_date": "$(date +%Y-%m-%d)",
    "content": {
      "en": "Terms of Service for $PLATFORM_NAME_EN. Please review and accept these terms to use our platform.",
      "fr": "Conditions d'utilisation pour $PLATFORM_NAME_FR. Veuillez lire et accepter ces conditions pour utiliser notre plateforme."
    }
  },
  "privacy_policy": {
    "effective_date": "$(date +%Y-%m-%d)",
    "content": {
      "en": "Privacy Policy for $PLATFORM_NAME_EN. We respect your privacy and protect your personal information.",
      "fr": "Politique de confidentialité pour $PLATFORM_NAME_FR. Nous respectons votre vie privée et protégeons vos informations personnelles."
    }
  },
  "data_controller": {
    "name": "$INSTANCE_DISPLAY",
    "email": "privacy@$DOMAIN"
  }
}
EOF

# ============================================
# Generate nginx Config
# ============================================
log "Generating nginx configuration..."

# Copy template and substitute variables
export DOMAIN CONTAINER_PREFIX

if [[ -f "nginx/conf.d/default.conf.template" ]]; then
    envsubst '${DOMAIN} ${CONTAINER_PREFIX}' \
        < nginx/conf.d/default.conf.template \
        > "$DEPLOY_PATH/nginx/conf.d/default.conf"
else
    # Create a basic config
    cat > "$DEPLOY_PATH/nginx/conf.d/default.conf" << NGINX
upstream backend {
    server ${CONTAINER_PREFIX}-backend:8000;
}

upstream frontend {
    server ${CONTAINER_PREFIX}-frontend:3000;
}

server {
    listen 80;
    server_name $DOMAIN;
    return 301 https://\$host\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name $DOMAIN;

    ssl_certificate /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;

    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }

    location /uploads/ {
        proxy_pass http://backend/data/uploads/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }

    location / {
        proxy_pass http://frontend;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
}
NGINX
fi

# Generate ntfy nginx config from template
if [[ -f "nginx/conf.d/ntfy.conf.template" ]]; then
    log "Generating ntfy nginx configuration..."
    envsubst '${DOMAIN} ${CONTAINER_PREFIX}' \
        < nginx/conf.d/ntfy.conf.template \
        > "$DEPLOY_PATH/nginx/conf.d/ntfy.conf"
fi

# ============================================
# Copy nginx.conf
# ============================================
if [[ -f "nginx/nginx.conf" ]]; then
    cp nginx/nginx.conf "$DEPLOY_PATH/nginx/nginx.conf"
fi

# ============================================
# Copy docker-compose.yml
# ============================================
if [[ -f "docker-compose.yml" ]]; then
    log "Copying docker-compose.yml..."
    cp docker-compose.yml "$DEPLOY_PATH/docker-compose.yml"
fi

# ============================================
# Copy Scripts
# ============================================
if [[ -d "scripts" ]]; then
    log "Copying deployment scripts..."
    mkdir -p "$DEPLOY_PATH/scripts"
    cp scripts/deploy.sh "$DEPLOY_PATH/scripts/" 2>/dev/null || true
    cp scripts/backup.sh "$DEPLOY_PATH/scripts/" 2>/dev/null || true
    chmod +x "$DEPLOY_PATH/scripts/"*.sh 2>/dev/null || true
fi

# ============================================
# SSL Setup Instructions
# ============================================
if [[ "$SKIP_SSL" != "true" ]]; then
    log "Creating SSL placeholder..."
    echo "# SSL certificates go here" > "$DEPLOY_PATH/ssl/README.md"
fi

# ============================================
# Summary
# ============================================
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                     Setup Complete!                                ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Created files:${NC}"
ls -la "$DEPLOY_PATH"
echo ""
echo -e "${CYAN}Next Steps:${NC}"
echo ""
echo "1. ${YELLOW}Review and update configuration:${NC}"
echo "   nano $DEPLOY_PATH/.env"
echo "   nano $DEPLOY_PATH/backend/config/platform.config.json"
echo ""
echo "2. ${YELLOW}Set up SSL certificates:${NC}"
echo "   # Option A: Let's Encrypt (recommended)"
echo "   certbot certonly --standalone -d $DOMAIN"
echo "   cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem $DEPLOY_PATH/ssl/"
echo "   cp /etc/letsencrypt/live/$DOMAIN/privkey.pem $DEPLOY_PATH/ssl/"
echo ""
echo "   # Option B: Self-signed (for testing)"
echo "   openssl req -x509 -nodes -days 365 -newkey rsa:2048 \\"
echo "     -keyout $DEPLOY_PATH/ssl/privkey.pem \\"
echo "     -out $DEPLOY_PATH/ssl/fullchain.pem"
echo ""
echo "3. ${YELLOW}Update IMAGE_REPOSITORY in .env${NC}"
echo "   Set to your Docker registry path"
echo ""
echo "4. ${YELLOW}Start the deployment:${NC}"
echo "   cd $DEPLOY_PATH"
echo "   docker compose pull"
echo "   docker compose up -d"
echo ""
echo "5. ${YELLOW}Initialize the database:${NC}"
echo "   docker compose exec backend python init_db.py"
echo ""
echo -e "${GREEN}Done!${NC} Your instance will be available at: https://$DOMAIN"
echo ""
