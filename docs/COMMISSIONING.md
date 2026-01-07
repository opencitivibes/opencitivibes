# OpenCitiVibes Commissioning Guide

This guide explains how to deploy a new OpenCitiVibes instance for any city, organization, or community.

## Overview

OpenCitiVibes is a white-label citizen engagement platform. Each deployment (instance) can be customized with:

- Custom branding (colors, logos, images)
- Instance-specific entity name (city, organization)
- Multiple language support
- Custom legal content (Terms, Privacy Policy)
- Configurable features

## Deployment Profiles

OpenCitiVibes uses Docker Compose profiles to manage different deployment environments:

| Profile | Email Service | Database | Use Case |
|---------|--------------|----------|----------|
| `dev` | Mailpit (email capture) | SQLite | Local development, testing email flows |
| `staging` | Postfix (SMTP relay) | SQLite | Pre-production testing with real emails |
| `prod` | Postfix (SMTP relay) | PostgreSQL | Production deployment |

### Quick Reference

```bash
# Development - emails captured in Mailpit web UI
docker compose --profile dev up -d

# Staging - real emails via Postfix, SQLite database
docker compose --profile staging up -d

# Production - real emails via Postfix, PostgreSQL database
docker compose --profile prod up -d
```

### Profile Components

| Service | dev | staging | prod |
|---------|-----|---------|------|
| nginx | ✓ | ✓ | ✓ |
| backend | ✓ | ✓ | ✓ |
| frontend | ✓ | ✓ | ✓ |
| ntfy | ✓ | ✓ | ✓ |
| mailpit | ✓ | - | - |
| postfix | - | ✓ | ✓ |
| postgres | - | - | ✓ |

## Prerequisites

- Linux server (Ubuntu 22.04+ recommended)
- Docker & Docker Compose v2
- Domain name with DNS configured
- HTTPS certificate (Let's Encrypt recommended)
- 2GB+ RAM, 20GB+ storage (4GB+ RAM for prod profile with PostgreSQL)

## Docker Setup

### Running Docker Without Sudo

To run Docker commands without `sudo`, add your user to the `docker` group:

```bash
# Add current user to docker group
sudo usermod -aG docker $USER

# Apply changes (or log out and back in)
newgrp docker

# Verify it works
docker ps
```

### File Permissions (Development)

The development Docker configuration (`docker-compose.dev.yml`) runs containers as your current user instead of root. This prevents permission issues with mounted volumes (e.g., `frontend/.next` or `backend/data` being owned by root).

**How it works:**
- The `docker-dev.sh` script automatically exports `DOCKER_UID` and `DOCKER_GID`
- Containers use `user: "${DOCKER_UID:-1000}:${DOCKER_GID:-1000}"` to run as your user
- Files created by containers are owned by you, not root

**If you encounter root-owned files:**

```bash
# Fix ownership of frontend build artifacts
sudo chown -R $USER:$USER frontend/.next frontend/node_modules

# Or simply remove and let Docker recreate them
sudo rm -rf frontend/.next
./scripts/docker-dev.sh down && ./scripts/docker-dev.sh up
```

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/opencitivibes.git
cd opencitivibes
```

### 2. Run Instance Setup

```bash
./scripts/setup-instance.sh <instance-name> <domain>

# Example for Montreal:
./scripts/setup-instance.sh montreal idees-montreal.ca

# Example for Paris:
./scripts/setup-instance.sh paris idees-paris.fr
```

### 3. Configure Your Instance

Edit the generated configuration files:

```bash
cd /opt/opencitivibes-<instance-name>

# 1. Update environment variables
nano .env

# 2. Configure platform identity
nano backend/config/platform.config.json

# 3. Customize legal content
nano backend/config/legal.config.json
```

### 4. Deploy

Choose the appropriate profile for your environment:

```bash
# Development (Mailpit + SQLite)
docker compose --profile dev up -d

# Staging (Postfix + SQLite)
docker compose --profile staging up -d

# Production (Postfix + PostgreSQL)
docker compose --profile prod up -d
```

### 5. Initialize Database

```bash
# For dev/staging (SQLite)
docker compose exec backend python init_db.py

# For prod (PostgreSQL) - ensure DATABASE_URL is set correctly
docker compose exec backend python init_db.py
```

### 6. Set Up SSL

```bash
# Initial setup (requests certs for domain and ntfy.domain)
./scripts/setup-ssl.sh <domain>

# Renewal (run periodically or via cron)
./scripts/setup-ssl.sh --renew <domain>

# Use webroot mode if nginx is already running
./scripts/setup-ssl.sh --webroot <domain>
```

The script automatically:
- Requests certificates for both main domain and `ntfy.` subdomain
- Copies certificates to the `ssl/` directory
- Sets correct permissions

## Configuration Reference

### Platform Configuration (`platform.config.json`)

| Field | Description | Required |
|-------|-------------|----------|
| `instance.name` | Display name for the platform | Yes |
| `instance.entity.type` | `city`, `region`, `organization`, `community` | Yes |
| `instance.entity.name` | Name of the entity (city name, org name) | Yes |
| `contact.email` | Contact email address | Yes |
| `localization.default_locale` | Default language (`en`, `fr`, etc.) | Yes |
| `localization.supported_locales` | List of supported languages | Yes |
| `branding.*` | Colors, logos, images | No |
| `legal.*` | Jurisdiction, courts, privacy authority | No |

### Environment Variables (`.env`)

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | JWT signing key | `openssl rand -hex 32` |
| `DATABASE_URL` | Database connection | See below |
| `ADMIN_EMAIL` | Initial admin email | `admin@example.com` |
| `DOMAIN` | Production domain | `ideas-example.com` |

**Database URL by Profile:**

| Profile | DATABASE_URL |
|---------|-------------|
| `dev` | `sqlite:///./data/opencitivibes.db` |
| `staging` | `sqlite:///./data/opencitivibes.db` |
| `prod` | `postgresql://user:pass@postgres:5432/opencitivibes` |

**PostgreSQL Configuration (prod profile):**

| Variable | Description | Example |
|----------|-------------|---------|
| `POSTGRES_USER` | PostgreSQL username | `opencitivibes` |
| `POSTGRES_PASSWORD` | PostgreSQL password | Generated secret |
| `POSTGRES_DB` | Database name | `opencitivibes` |

See `.env.example` for complete list.

## Customization

### Adding Languages

1. Create translation file: `frontend/src/i18n/locales/<lang>.json`
2. Copy structure from `en.json`
3. Translate all keys
4. Add language to `localization.supported_locales` in config

### Custom Branding

```json
{
  "branding": {
    "primary_color": "#1D4ED8",
    "secondary_color": "#1E3A8A",
    "hero_image": "/instances/yourinstance/hero.jpg",
    "logo": "/instances/yourinstance/logo.svg"
  }
}
```

### Legal Content

Customize `backend/config/legal.config.json` with your jurisdiction's requirements.

### Admin Push Notifications (Ntfy)

OpenCitiVibes includes a self-hosted [ntfy](https://ntfy.sh) service for admin push notifications. Admins receive real-time alerts on their mobile devices when content requires moderation.

#### Security Configuration

**Important:** The ntfy web interface is blocked by default for security. Only API endpoints are exposed:

| Endpoint | Access | Purpose |
|----------|--------|---------|
| `/<topic>/json,sse,ws,raw` | Public (with auth) | Mobile app subscriptions |
| `POST/PUT /<topic>` | Public (with auth) | Backend publishing |
| `/v1/account` | Public | Mobile app authentication |
| `/v1/health` | Internal only | Health checks |
| `/settings`, `/login`, `/app`, etc. | **Blocked (404)** | Web UI disabled |

This prevents information disclosure and reduces attack surface. Admins must use the mobile app.

#### Enable Notifications

1. Configure environment variables in `.env`:

```bash
# Internal URL (Docker network)
NTFY_URL=http://ntfy:80
NTFY_TOPIC_PREFIX=admin
NTFY_ENABLED=true
APP_URL=https://yourdomain.com

# Public URL for mobile apps
NTFY_BASE_URL=https://ntfy.yourdomain.com
```

2. Add DNS record for `ntfy.yourdomain.com` pointing to your server
   - **Important:** If using Cloudflare, set this record to **DNS only** (grey cloud, not proxied)
   - Ntfy uses WebSockets/SSE which work better without Cloudflare proxy

3. Configure SSL for the ntfy subdomain (included in `setup-ssl.sh`)

#### Set Up Admin Access

After deployment, create admin users and configure access:

```bash
# Create admin user for notifications
docker exec ${CONTAINER_PREFIX}-ntfy ntfy user add admin1

# Grant read access to admin topics
docker exec ${CONTAINER_PREFIX}-ntfy ntfy access admin1 "${NTFY_TOPIC_PREFIX}-*" read

# Generate auth token for backend (if using auth)
docker exec ${CONTAINER_PREFIX}-ntfy ntfy token add --label="backend" backend-publisher
# Add the token to .env as NTFY_AUTH_TOKEN
```

#### Admin Mobile Setup

Each admin installs the ntfy app and subscribes to topics:

1. Install ntfy app ([iOS](https://apps.apple.com/app/ntfy/id1625396347) / [Android](https://play.google.com/store/apps/details?id=io.heckel.ntfy))
2. Add server: `https://ntfy.yourdomain.com`
3. Enter credentials (username/password from setup)
4. Subscribe to: `admin-ideas`, `admin-appeals`, `admin-reports`, etc.

See [Ntfy Notification System](../claude-docs/plans/ntfy-notification-system.md) for detailed configuration.

### Transactional Email (Passwordless Login)

OpenCitiVibes supports passwordless authentication via email codes. Email configuration is determined by the deployment profile:

| Profile | Email Service | Configuration |
|---------|---------------|---------------|
| `dev` | Mailpit | Visual email inbox at `/mailpit/` - no actual delivery |
| `staging` | Postfix | Self-hosted SMTP relay with DKIM - real emails |
| `prod` | Postfix | Self-hosted SMTP relay with DKIM - real emails |

#### Development Profile: Mailpit

The `dev` profile includes Mailpit, which captures all outgoing emails for testing.

```bash
# Start with dev profile
docker compose --profile dev up -d

# Access inbox at https://yourdomain.com/mailpit/
```

Environment variables for dev:
```bash
EMAIL_PROVIDER=smtp
SMTP_HOST=mailpit
SMTP_PORT=1025
SMTP_USE_TLS=false
SMTP_USE_SSL=false
SMTP_FROM_EMAIL=noreply@yourdomain.com
SMTP_FROM_NAME=OpenCitiVibes
```

#### Staging/Production Profiles: Postfix SMTP Relay

The `staging` and `prod` profiles include Postfix, a self-hosted SMTP relay with automatic DKIM signing.

```bash
# Environment variables in .env
EMAIL_PROVIDER=smtp
SMTP_HOST=postfix
SMTP_PORT=25
SMTP_USE_TLS=false
SMTP_USE_SSL=false
SMTP_FROM_EMAIL=admin@yourdomain.com
SMTP_FROM_NAME=Your Instance Name
MAIL_DOMAIN=yourdomain.com

# Start with staging or prod profile
docker compose --profile staging up -d
# or
docker compose --profile prod up -d
```

##### DNS Records for Email Deliverability

Configure these DNS records to ensure emails aren't marked as spam:

**1. SPF Record** (TXT on root domain):
```
v=spf1 ip4:YOUR_SERVER_IP -all
```

**2. DKIM Record** (TXT on `mail._domainkey`):
```bash
# Get DKIM public key from container
docker exec ${CONTAINER_PREFIX}-postfix cat /etc/opendkim/keys/yourdomain.com/mail.txt
```
Add the output as a TXT record for `mail._domainkey.yourdomain.com`.

**3. DMARC Record** (TXT on `_dmarc`):
```
v=DMARC1; p=quarantine; rua=mailto:admin@yourdomain.com
```

##### Firewall Configuration

Ensure outbound port 25 is open:
```bash
sudo ufw allow out 25/tcp
```

Note: Many cloud providers block outbound port 25 by default. Check with your VPS provider if emails aren't being delivered.

##### Verify Email Delivery

```bash
# Send test email
docker exec ${CONTAINER_PREFIX}-backend python -c "
from services.email_service import EmailService
EmailService.send_login_code('test@example.com', '123456', 'Test User')
"

# Check Postfix logs
docker logs ${CONTAINER_PREFIX}-postfix --tail 50
```

#### External SMTP Services

You can also use external SMTP services (SendGrid, Mailgun, etc.):

```bash
EMAIL_PROVIDER=smtp
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USE_SSL=false
SMTP_USER=apikey
SMTP_PASSWORD=your-sendgrid-api-key
SMTP_FROM_EMAIL=noreply@yourdomain.com
SMTP_FROM_NAME=Your Instance Name
```

For SendGrid API (alternative to SMTP):
```bash
EMAIL_PROVIDER=sendgrid
SENDGRID_API_KEY=your-api-key
SMTP_FROM_EMAIL=noreply@yourdomain.com
SMTP_FROM_NAME=Your Instance Name
```

## Maintenance

### Automated Cleanup (Cron Jobs)

To prevent disk exhaustion, install the maintenance scripts on your VPS:

```bash
# Copy scripts to VPS
scp scripts/vps-maintenance.sh scripts/vps-disk-alert.sh scripts/setup-vps-maintenance.sh \
    ubuntu@your-vps:/home/ubuntu/maintenance/

# SSH and run setup
ssh ubuntu@your-vps
chmod +x /home/ubuntu/maintenance/*.sh
bash /home/ubuntu/maintenance/setup-vps-maintenance.sh
```

**Installed cron jobs:**

| Schedule | Task | Description |
|----------|------|-------------|
| Sunday 3 AM | `vps-maintenance.sh` | Full cleanup (Docker, logs, kernels, apt cache) |
| Daily 4 AM | `docker image prune` | Remove unused images older than 72h |
| Every 6 hours | `vps-disk-alert.sh` | Alert via ntfy if disk >80% |
| Daily 5 AM | `logrotate` | Rotate system logs |

**What gets cleaned:**
- Docker: unused images, build cache, dangling volumes (>7 days old)
- System: old kernels, apt cache, temp files
- Logs: journald (capped at 100MB/7 days), large log files (>100MB)

**Monitor:**
```bash
# View maintenance logs
tail -f /var/log/vps-maintenance.log

# Check disk usage
df -h /

# Check Docker usage
docker system df
```

### Backups

```bash
./scripts/backup.sh
# Backups stored in /opt/opencitivibes-<instance>/backups/
```

### Updates

```bash
docker compose pull
docker compose up -d
```

### Logs

```bash
docker compose logs -f backend
docker compose logs -f frontend
```

## Troubleshooting

### Common Issues

#### Services not starting
```bash
# Check container status
docker compose ps

# View logs
docker compose logs backend
docker compose logs frontend
```

#### Database connection errors
```bash
# Verify DATABASE_URL in .env
# Ensure data directory exists and has correct permissions
ls -la data/
```

#### SSL certificate issues
```bash
# Check nginx configuration
docker compose exec nginx nginx -t

# Check certificate expiry
sudo certbot certificates

# Renew certificates (stops nginx, renews, restarts)
./scripts/setup-ssl.sh --renew <domain>

# If certificate doesn't include ntfy subdomain, expand it
sudo certbot certonly --standalone \
  -d yourdomain.com \
  -d ntfy.yourdomain.com \
  --expand
```

#### Configuration not loading
```bash
# Validate JSON syntax
python -m json.tool backend/config/platform.config.json

# Check config path in .env
grep PLATFORM_CONFIG_PATH .env
```

#### Push notifications not working
```bash
# Check ntfy container is healthy
docker compose ps ntfy

# View ntfy logs
docker compose logs ntfy

# Test internal connectivity from backend
docker exec ${CONTAINER_PREFIX}-backend curl -s http://ntfy:80/v1/health

# Test notification publish
docker exec ${CONTAINER_PREFIX}-backend curl -X POST \
  -H "Title: Test" -d "Test message" \
  http://ntfy:80/admin-ideas

# Check NTFY_URL is set in backend
docker exec ${CONTAINER_PREFIX}-backend env | grep NTFY
```

#### Email/login codes not working
```bash
# Check email provider configuration
docker exec ${CONTAINER_PREFIX}-backend env | grep -E "EMAIL|SMTP"

# View email logs (console provider)
docker compose logs backend | grep -i email

# Check Postfix container (production)
docker compose ps postfix
docker logs ${CONTAINER_PREFIX}-postfix --tail 50

# Test DNS resolution to Postfix
docker exec ${CONTAINER_PREFIX}-backend ping -c 1 postfix

# Verify SMTP connectivity
docker exec ${CONTAINER_PREFIX}-backend python -c "
import smtplib
s = smtplib.SMTP('postfix', 25)
print(s.noop())
s.quit()
"

# Check if port 25 is blocked (from VPS)
nc -zv smtp.gmail.com 25 || echo "Port 25 blocked by provider"
```

### Getting Help

- Check the [Configuration Reference](CONFIGURATION.md)
- Review the [Testing Checklist](TESTING_CHECKLIST.md)
- Open an issue on the GitHub repository

## DNS Configuration with Cloudflare

If using Cloudflare for DNS, configure proxy status as follows:

| Record | Type | Value | Proxy Status | Reason |
|--------|------|-------|--------------|--------|
| `yourdomain.com` | A | VPS IP | **Proxied** (orange) | DDoS protection, CDN |
| `ntfy.yourdomain.com` | A | VPS IP | **DNS only** (grey) | WebSocket/SSE performance |
| `ssh.yourdomain.com` | A | VPS IP | **DNS only** (grey) | SSH access (port 22) |

**Why some records should not be proxied:**
- Cloudflare only proxies HTTP/HTTPS (ports 80/443)
- SSH (port 22) won't work through Cloudflare proxy
- Ntfy's real-time features (WebSockets, SSE) work better without proxy

## Staging Environment Setup

For testing deployments before production, use the automated staging setup script.

### Prerequisites

- Ubuntu VPS with Docker installed (rootless or with sudo)
- Domain name pointing to VPS (e.g., `staging.yourdomain.com`)
- GitHub account with access to the container registry

### Quick Setup

> **⚠️ WARNING: FOR FRESH VPS ONLY!**
>
> The setup scripts OVERWRITE configuration files (.env, docker-compose.yml, nginx configs, etc.).
> **DO NOT run on existing deployments** - you will lose your configuration!
> For updates to existing deployments, use `deploy.sh` or manually update specific files.

```bash
# SSH to your VPS
ssh ubuntu@your-staging-vps

# Download and run the setup script
curl -sL https://raw.githubusercontent.com/opencitivibes/opencitivibes/main/scripts/setup-staging-vps.sh | bash
```

The script creates:
- `.env` with generated secrets and configurable admin email
- `docker-compose.yml` from the repository
- `nginx/nginx.conf` - main nginx configuration
- `nginx/conf.d/default.conf` - generated from template (main site)
- `nginx/conf.d/ntfy.conf` - generated from template (ntfy API, web UI blocked)
- `ntfy/server.yml` - ntfy configuration with auth enabled
- `backend/config/platform.config.json` with correct schema
- `instance-assets/` directory for hero.png and logo.svg
- `seed-admin.sh` for creating the admin user

**Note:** Nginx configs are downloaded as templates from GitHub and processed with `envsubst` to substitute `${DOMAIN}` and `${CONTAINER_PREFIX}`. The ntfy config blocks the web interface for security - only API endpoints are exposed.

### Post-Setup Steps

After running the script, complete these manual steps:

```bash
cd ~/opencitivibes

# 1. (Rootless Docker only) Allow privileged ports
echo 'net.ipv4.ip_unprivileged_port_start=80' | sudo tee -a /etc/sysctl.conf
sudo sysctl -p

# 2. Set up SSL certificates
sudo apt install certbot
sudo certbot certonly --standalone -d your-domain.com
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem ssl/
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem ssl/
sudo chown ubuntu:ubuntu ssl/*

# 3. Login to GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io -u your-username --password-stdin

# 4. Upload instance assets (BEFORE starting containers)
scp hero.png logo.svg ubuntu@your-vps:~/opencitivibes/instance-assets/

# 5. Pull and start containers (staging profile)
docker compose --profile staging pull
docker compose --profile staging up -d

# 6. Seed admin user
./seed-admin.sh
```

**Important:** Instance assets (hero.png, logo.svg) are mounted via Docker volume from `./instance-assets/` to `/app/public/instance/`. Upload them **before** starting containers. If you add or update assets after containers are running, restart the frontend:

```bash
docker compose --profile staging restart frontend
```

Note: The setup script automatically patches docker-compose.yml to:
- Use local `./ssl` directory instead of Docker volume
- Add `HOSTNAME=0.0.0.0` for frontend health checks
- Fix health check URL for IPv4 compatibility

### Configuration

Edit these files before deployment:

| File | Purpose |
|------|---------|
| `.env` | Environment variables, admin credentials |
| `backend/config/platform.config.json` | Instance branding, localization |
| `instance-assets/hero.png` | Hero banner image (homepage) |
| `instance-assets/logo.svg` | Platform logo (header, footer) |

The `instance-assets/` directory is volume-mounted to `/app/public/instance/` in the frontend container. Files are accessible at `https://yourdomain.com/instance/hero.png` and `https://yourdomain.com/instance/logo.svg`.

### Troubleshooting Staging

```bash
# View container logs (use correct profile)
docker compose --profile staging logs -f backend
docker compose --profile staging logs -f frontend
docker compose --profile staging logs -f nginx

# Check container health status
docker compose --profile staging ps

# If backend shows migration errors, seed-admin.sh handles this automatically
# For manual fix:
docker exec your-prefix-backend alembic stamp head
docker compose --profile staging restart backend
```

## Production Environment Setup

Production setup uses the same approach as staging but with PostgreSQL:

> **⚠️ WARNING: FOR FRESH VPS ONLY!** Same warning as staging - this script overwrites all configuration files.

```bash
# SSH to your production VPS
ssh ubuntu@your-production-vps

# Download and run the production setup script
curl -sL https://raw.githubusercontent.com/opencitivibes/opencitivibes/main/scripts/setup-production-vps.sh | bash
```

Key differences from staging:
- Uses PostgreSQL instead of SQLite (`--profile prod`)
- Generates `POSTGRES_PASSWORD` automatically
- Creates PostgreSQL-aware backup script

The script downloads nginx templates from GitHub and generates configs with your domain/container prefix. Follow the same post-setup steps as staging, but use `--profile prod` for all Docker commands.

## Security Considerations

1. **Always change default passwords** - Never use default admin credentials in production
2. **Use strong SECRET_KEY** - Generate with `openssl rand -hex 32`
3. **Enable HTTPS** - Required for production deployments
4. **Regular backups** - Configure automated backup scripts
5. **Keep updated** - Regularly pull latest security patches
6. **Ntfy web UI blocked** - The setup scripts configure nginx to block ntfy's web interface (`/settings`, `/login`, etc.) - only API endpoints are exposed to prevent information disclosure

## Next Steps

After deployment:

1. [ ] Verify all functionality using [Testing Checklist](TESTING_CHECKLIST.md)
2. [ ] Configure backup schedule
3. [ ] Set up monitoring (optional)
4. [ ] Configure admin push notifications (see [Admin Push Notifications](#admin-push-notifications-ntfy))
5. [ ] Configure email for passwordless login (see [Transactional Email](#transactional-email-passwordless-login))
6. [ ] Set up DNS records for email deliverability (SPF, DKIM, DMARC)
7. [ ] Announce to your community
