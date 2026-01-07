#!/bin/bash
# ============================================
# OpenCitiVibes SSL Certificate Setup Script
# ============================================
# Sets up Let's Encrypt SSL certificates for the main domain and ntfy subdomain.
#
# Usage:
#   ./setup-ssl.sh <domain>           # Initial setup (standalone mode)
#   ./setup-ssl.sh --renew <domain>   # Renew existing certificates
#   ./setup-ssl.sh --webroot <domain> # Use webroot mode (nginx must be running)
#
# Examples:
#   ./setup-ssl.sh ideespourmontreal.opencitivibes.ovh
#   ./setup-ssl.sh --renew ideespourmontreal.opencitivibes.ovh
# ============================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default configuration
DEPLOY_DIR="${DEPLOY_DIR:-$(pwd)}"
SSL_DIR="${DEPLOY_DIR}/ssl"
WEBROOT_DIR="/var/www/certbot"

# Parse arguments
RENEW=false
WEBROOT=false
DOMAIN=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --renew)
            RENEW=true
            shift
            ;;
        --webroot)
            WEBROOT=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [options] <domain>"
            echo ""
            echo "Options:"
            echo "  --renew    Renew existing certificates"
            echo "  --webroot  Use webroot mode (nginx must be running)"
            echo "  -h, --help Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0 ideespourmontreal.opencitivibes.ovh"
            echo "  $0 --renew ideespourmontreal.opencitivibes.ovh"
            exit 0
            ;;
        *)
            DOMAIN="$1"
            shift
            ;;
    esac
done

if [ -z "$DOMAIN" ]; then
    echo -e "${RED}Error: Domain is required${NC}"
    echo "Usage: $0 [--renew] [--webroot] <domain>"
    exit 1
fi

echo "=== OpenCitiVibes SSL Setup ==="
echo "Domain: $DOMAIN"
echo "Ntfy subdomain: ntfy.$DOMAIN"
echo "SSL directory: $SSL_DIR"
echo ""

# Check if certbot is installed
if ! command -v certbot &> /dev/null; then
    echo -e "${YELLOW}Certbot not found. Installing...${NC}"
    sudo apt update
    sudo apt install -y certbot
fi

# Create SSL directory if it doesn't exist
mkdir -p "$SSL_DIR"

# Function to copy certificates to deploy directory
copy_certs() {
    local domain=$1
    echo -e "${GREEN}Copying certificates to $SSL_DIR...${NC}"

    # Find the certificate directory (could be main domain or wildcard)
    local cert_dir="/etc/letsencrypt/live/$domain"

    if [ ! -d "$cert_dir" ]; then
        echo -e "${RED}Certificate directory not found: $cert_dir${NC}"
        echo "Available certificates:"
        sudo ls -la /etc/letsencrypt/live/ 2>/dev/null || echo "No certificates found"
        return 1
    fi

    sudo cp "$cert_dir/fullchain.pem" "$SSL_DIR/"
    sudo cp "$cert_dir/privkey.pem" "$SSL_DIR/"

    # Fix permissions
    sudo chown $(whoami):$(whoami) "$SSL_DIR"/*.pem
    chmod 644 "$SSL_DIR/fullchain.pem"
    chmod 600 "$SSL_DIR/privkey.pem"

    echo -e "${GREEN}Certificates copied successfully!${NC}"
    ls -la "$SSL_DIR"
}

# Renewal mode
if [ "$RENEW" = true ]; then
    echo "=== Renewing Certificates ==="

    if [ "$WEBROOT" = true ]; then
        # Webroot renewal (nginx running)
        echo "Using webroot mode (nginx must be serving $WEBROOT_DIR)"
        sudo certbot renew --webroot -w "$WEBROOT_DIR"
    else
        # Standalone renewal (stop nginx first)
        echo "Using standalone mode (stopping nginx if running)..."

        # Try to stop nginx container
        docker compose --profile prod stop nginx 2>/dev/null || \
        docker compose --profile staging stop nginx 2>/dev/null || \
        sudo systemctl stop nginx 2>/dev/null || true

        sudo certbot renew --standalone

        # Restart nginx
        docker compose --profile prod start nginx 2>/dev/null || \
        docker compose --profile staging start nginx 2>/dev/null || \
        sudo systemctl start nginx 2>/dev/null || true
    fi

    # Copy renewed certificates
    copy_certs "$DOMAIN"

    # Reload nginx to pick up new certs
    echo "Reloading nginx configuration..."
    docker compose --profile prod exec nginx nginx -s reload 2>/dev/null || \
    docker compose --profile staging exec nginx nginx -s reload 2>/dev/null || \
    sudo systemctl reload nginx 2>/dev/null || true

    echo -e "${GREEN}=== Certificate renewal complete! ===${NC}"
    exit 0
fi

# Initial setup mode
echo "=== Initial Certificate Setup ==="

# Check if port 80 is available (required for standalone mode)
if ! [ "$WEBROOT" = true ]; then
    if ss -tlnp | grep -q ':80 '; then
        echo -e "${YELLOW}Warning: Port 80 is in use. Stopping services...${NC}"

        # Try to stop nginx container
        docker compose --profile prod stop nginx 2>/dev/null || \
        docker compose --profile staging stop nginx 2>/dev/null || \
        sudo systemctl stop nginx 2>/dev/null || true

        sleep 2

        if ss -tlnp | grep -q ':80 '; then
            echo -e "${RED}Error: Port 80 is still in use after stopping nginx.${NC}"
            echo "Please stop all services using port 80 and try again."
            ss -tlnp | grep ':80 '
            exit 1
        fi
    fi
fi

# Request certificate for both main domain and ntfy subdomain
echo "Requesting certificates for:"
echo "  - $DOMAIN"
echo "  - ntfy.$DOMAIN"
echo ""

if [ "$WEBROOT" = true ]; then
    # Create webroot directory
    sudo mkdir -p "$WEBROOT_DIR"

    # Use webroot mode
    sudo certbot certonly \
        --webroot \
        -w "$WEBROOT_DIR" \
        -d "$DOMAIN" \
        -d "ntfy.$DOMAIN" \
        --non-interactive \
        --agree-tos \
        --email "admin@$DOMAIN" \
        --expand
else
    # Use standalone mode
    sudo certbot certonly \
        --standalone \
        -d "$DOMAIN" \
        -d "ntfy.$DOMAIN" \
        --non-interactive \
        --agree-tos \
        --email "admin@$DOMAIN" \
        --expand
fi

# Copy certificates
copy_certs "$DOMAIN"

# Restart nginx if it was running
docker compose --profile prod start nginx 2>/dev/null || \
docker compose --profile staging start nginx 2>/dev/null || \
sudo systemctl start nginx 2>/dev/null || true

echo ""
echo -e "${GREEN}=== SSL Setup Complete ===${NC}"
echo ""
echo "Certificates installed to: $SSL_DIR"
echo "  - fullchain.pem"
echo "  - privkey.pem"
echo ""
echo "Next steps:"
echo "1. Ensure your nginx configuration references these certificates"
echo "2. Restart nginx: docker compose --profile prod restart nginx"
echo ""
echo "To auto-renew certificates, add this cron job:"
echo "  0 0 1 * * cd $DEPLOY_DIR && ./scripts/setup-ssl.sh --renew $DOMAIN"
echo ""
echo "Or set up a systemd timer for automatic renewal:"
echo "  sudo systemctl enable --now certbot.timer"
