# OpenCitiVibes Commissioning Guide

This guide explains how to deploy a new OpenCitiVibes instance for any city, organization, or community.

## Overview

OpenCitiVibes is a white-label citizen engagement platform. Each deployment (instance) can be customized with:

- Custom branding (colors, logos, images)
- Instance-specific entity name (city, organization)
- Multiple language support
- Custom legal content (Terms, Privacy Policy)
- Configurable features

## Prerequisites

- Linux server (Ubuntu 22.04+ recommended)
- Docker & Docker Compose v2
- Domain name with DNS configured
- HTTPS certificate (Let's Encrypt recommended)
- 2GB+ RAM, 20GB+ storage

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

```bash
docker compose up -d
```

### 5. Initialize Database

```bash
docker compose exec backend python init_db.py
```

### 6. Set Up SSL

```bash
./scripts/setup-ssl.sh <domain>
```

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
| `DATABASE_URL` | Database connection | `sqlite:///./data/opencitivibes.db` |
| `ADMIN_EMAIL` | Initial admin email | `admin@example.com` |
| `DOMAIN` | Production domain | `ideas-example.com` |

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

3. Configure SSL for the ntfy subdomain

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

## Maintenance

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

# Renew certificates
./scripts/setup-ssl.sh --renew <domain>
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

### Getting Help

- Check the [Configuration Reference](CONFIGURATION.md)
- Review the [Testing Checklist](TESTING_CHECKLIST.md)
- Open an issue on the GitHub repository

## Staging Environment Setup

For testing deployments before production, use the automated staging setup script.

### Prerequisites

- Ubuntu VPS with Docker installed (rootless or with sudo)
- Domain name pointing to VPS (e.g., `staging.yourdomain.com`)
- GitHub account with access to the container registry

### Quick Setup

```bash
# SSH to your VPS
ssh ubuntu@your-staging-vps

# Download and run the setup script
curl -sL https://raw.githubusercontent.com/opencitivibes/opencitivibes/main/scripts/setup-staging-vps.sh | bash
```

The script creates:
- `.env` with generated secrets and configurable admin email
- `docker-compose.yml` from the repository
- `nginx/` configuration for reverse proxy with SSL
- `ntfy/` configuration for push notifications
- `backend/config/platform.config.json` with correct schema
- `deploy-instance-assets.sh` helper script
- `seed-admin.sh` for creating the admin user

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

# 4. Upload instance assets
scp hero.png logo.svg ubuntu@your-vps:~/opencitivibes/instance-assets/

# 5. Pull and start containers
docker compose pull
docker compose up -d

# 6. Deploy instance assets and seed admin
./deploy-instance-assets.sh
./seed-admin.sh
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
| `instance-assets/` | Hero image, logo |

### Troubleshooting Staging

```bash
# View container logs
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f nginx

# Check container health status
docker compose ps

# If backend shows migration errors, seed-admin.sh handles this automatically
# For manual fix:
docker exec your-prefix-backend alembic stamp head
docker compose restart backend
```

## Security Considerations

1. **Always change default passwords** - Never use default admin credentials in production
2. **Use strong SECRET_KEY** - Generate with `openssl rand -hex 32`
3. **Enable HTTPS** - Required for production deployments
4. **Regular backups** - Configure automated backup scripts
5. **Keep updated** - Regularly pull latest security patches

## Next Steps

After deployment:

1. [ ] Verify all functionality using [Testing Checklist](TESTING_CHECKLIST.md)
2. [ ] Configure backup schedule
3. [ ] Set up monitoring (optional)
4. [ ] Configure admin push notifications (see [Admin Push Notifications](#admin-push-notifications-ntfy))
5. [ ] Configure email for passwordless login (optional)
6. [ ] Announce to your community
