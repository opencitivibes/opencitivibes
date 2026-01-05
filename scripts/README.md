# Scripts

## Overview

| Script | Purpose |
|--------|---------|
| `switch-instance.sh` | Switch between platform instances (montreal, quebec, etc.) |
| `start-dev.sh` | Start both frontend and backend dev servers |
| `docker-dev.sh` | Docker development tool for local and remote deployments |
| `deploy.sh` | Production deployment with health checks and rollback |
| `backup.sh` | Database and configuration backup |
| `setup-instance.sh` | Create new OpenCitiVibes instance deployments |
| `opencitivibes.service.template` | systemd service template |

---

## switch-instance.sh

Switch between platform instances for local development. Each instance has its own database, branding, and configuration.

### Usage

```bash
./scripts/switch-instance.sh [instance|clean|status]
```

### Commands

| Command | Description |
|---------|-------------|
| `<instance>` | Switch to the specified instance (e.g., `montreal`, `quebec`) |
| `status` | Show current instance and list available instances |
| `clean` | Clean frontend caches and instance assets |

### Examples

```bash
# Switch to Montreal instance
./scripts/switch-instance.sh montreal

# Switch to Quebec instance
./scripts/switch-instance.sh quebec

# Check current instance
./scripts/switch-instance.sh status

# Clean caches
./scripts/switch-instance.sh clean
```

### What It Does

1. **Frontend setup:**
   - Cleans `.next/` and `node_modules/.cache/`
   - Copies instance images to `frontend/public/instance/`

2. **Backend setup:**
   - Symlinks `backend/config/platform.config.active.json` to instance config
   - Creates `backend/.env.instance` with exported `DATABASE_URL` and `PLATFORM_CONFIG_PATH`

### Instance Configuration

Instances are defined in `/instances/<name>/`:

```
instances/
├── montreal/
│   ├── platform.config.json    # Full config (branding, database, legal, etc.)
│   └── images/
│       ├── hero.png
│       └── logo.svg
└── quebec/
    ├── platform.config.json
    └── images/
        ├── hero.svg
        └── logo.svg
```

The `platform.config.json` includes:
- `instance.id` - Instance identifier
- `instance.name` - Localized names
- `database.file` - Database filename (in `backend/data/`)
- `branding` - Colors, logo paths, hero image
- `localization` - Supported locales
- `contact`, `legal`, `features` - Instance-specific settings

---

## start-dev.sh

Start both frontend and backend development servers with the active instance configuration.

### Usage

```bash
./scripts/start-dev.sh
```

### What It Does

1. Checks if an instance is configured (via `backend/.env.instance`)
2. Kills any existing dev servers
3. Starts backend on port 8000
4. Starts frontend on port 3000
5. Handles Ctrl+C to stop both servers

### Example

```bash
# First, switch to an instance
./scripts/switch-instance.sh montreal

# Then start dev servers
./scripts/start-dev.sh
```

Output:
```
=== Starting Dev Servers ===
Instance: montreal

[Backend] Starting on port 8000...
[Frontend] Starting on port 3000...

=== Servers Started ===
  Frontend: http://localhost:3000
  Backend:  http://localhost:8000
  API Docs: http://localhost:8000/docs

Press Ctrl+C to stop both servers
```

### Manual Alternative

If you prefer to run servers separately:

```bash
# Terminal 1: Backend
cd backend && source .env.instance && uv run uvicorn main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend && pnpm dev
```

---

## docker-dev.sh

Docker development tool for local and remote VM deployments.

### Usage

```bash
./scripts/docker-dev.sh [options] [command]
```

### Options

| Option | Description |
|--------|-------------|
| `--remote [user@host]` | Execute on remote VM. Uses `.docker-remote.env` if no host provided |
| `--sync` | Sync project files to remote before command (rsync) |
| `--dry-run` | Show commands without executing |

### Commands

| Command | Description |
|---------|-------------|
| `up` | Start development environment (localhost only) |
| `up-mobile` | Start with local network access (for mobile testing) |
| `down` | Stop development environment |
| `restart` | Restart all services |
| `build` | Rebuild containers (no cache) |
| `clean` | Remove containers and volumes |
| `status` / `ps` | Show container status |
| `logs` | Follow logs from all services |
| `logs-b` | Follow logs from backend only |
| `logs-f` | Follow logs from frontend only |
| `backend` | Open shell in backend container |
| `frontend` | Open shell in frontend container |
| `db-init` | Initialize database (categories + admin) |
| `db-reset` | Reset database to empty state |
| `db-seed` | Seed database with test data |
| `db-migrate` | Run Alembic migrations |
| `test` | Run all tests (backend + frontend) |
| `test-b` | Run backend tests only |
| `test-f` | Run frontend lint/typecheck only |

### Local Development

```bash
# Start the development environment (localhost only)
./scripts/docker-dev.sh up

# View logs
./scripts/docker-dev.sh logs

# Open backend shell
./scripts/docker-dev.sh backend

# Run tests
./scripts/docker-dev.sh test

# Rebuild containers
./scripts/docker-dev.sh build

# Stop everything
./scripts/docker-dev.sh down
```

### Mobile Testing

To test on mobile devices (phone, tablet) connected to the same network:

```bash
# Start with local network access
./scripts/docker-dev.sh up-mobile
```

This will:
1. Auto-detect your laptop's local IP address
2. Configure the frontend to be accessible on the network
3. Configure CORS to allow requests from mobile devices
4. Display the URL to open on your mobile device

Example output:
```
Mobile testing mode enabled
  Host IP: 192.168.1.42

Services accessible on local network:
  Frontend: http://192.168.1.42:3000
  Backend:  http://192.168.1.42:8000

On your mobile device, open: http://192.168.1.42:3000
```

**Requirements:**
- Mobile device must be on the same WiFi network as your laptop
- Firewall must allow connections on ports 3000 and 8000

### Remote VM Deployment

#### Option 1: Explicit Host

```bash
# Deploy to remote VM
./scripts/docker-dev.sh --remote user@192.168.1.100 up

# Sync files and rebuild
./scripts/docker-dev.sh --remote user@192.168.1.100 --sync build

# Check status on remote
./scripts/docker-dev.sh --remote user@192.168.1.100 status

# View remote logs
./scripts/docker-dev.sh --remote user@192.168.1.100 logs
```

#### Option 2: Config File

Create a config file for repeated use:

```bash
cp .docker-remote.env.example .docker-remote.env
```

Edit `.docker-remote.env`:

```bash
DOCKER_REMOTE_HOST=matt@192.168.1.100
DOCKER_REMOTE_PATH=/home/matt/opencitivibes
DOCKER_REMOTE_SYNC=false
DOCKER_REMOTE_SSH_OPTS=
```

Then use without specifying the host:

```bash
./scripts/docker-dev.sh --remote up
./scripts/docker-dev.sh --remote --sync build
./scripts/docker-dev.sh --remote logs
```

---

## deploy.sh

Production deployment script with health checks, backup, and rollback support.

### Usage

```bash
./scripts/deploy.sh [OPTIONS]
```

### Options

| Option | Description |
|--------|-------------|
| `--rollback` | Show rollback information for previous deployment |
| `--no-backup` | Skip pre-deployment backup |
| `--force` | Force deployment without health checks |
| `-h, --help` | Show help message |

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DEPLOY_PATH` | Current directory | Path to deployment directory |
| `COMPOSE_PROJECT_NAME` | `opencitivibes` | Docker Compose project name |
| `BACKUP_BEFORE_DEPLOY` | `true` | Create backup before deployment |
| `HEALTH_CHECK_TIMEOUT` | `60` | Timeout in seconds for health checks |

### Examples

```bash
# Normal deployment (with backup and health checks)
./scripts/deploy.sh

# Quick deployment without backup
./scripts/deploy.sh --no-backup

# Force deployment (skip health checks)
./scripts/deploy.sh --force

# Show rollback information
./scripts/deploy.sh --rollback
```

### What It Does

1. **Checks requirements** - Validates .env, docker-compose.yml, Docker availability
2. **Creates backup** - Runs backup.sh before deployment (unless --no-backup)
3. **Stores current state** - Saves current image digests for rollback reference
4. **Generates nginx config** - Substitutes environment variables in template
5. **Pulls latest images** - `docker compose pull`
6. **Deploys containers** - `docker compose up -d --remove-orphans`
7. **Waits for health** - Monitors container health status
8. **Verifies deployment** - Confirms all containers are running
9. **Cleans up** - Removes old images and unused resources

---

## backup.sh

Database and configuration backup script supporting SQLite and PostgreSQL.

### Usage

```bash
./scripts/backup.sh [OPTIONS]
```

### Options

| Option | Description |
|--------|-------------|
| `--db-only` | Only backup database |
| `--config-only` | Only backup configuration files |
| `--no-cleanup` | Skip cleanup of old backups |
| `-h, --help` | Show help message |

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DEPLOY_PATH` | Current directory | Path to deployment directory |
| `BACKUP_DIR` | `$DEPLOY_PATH/backups` | Directory for backups |
| `CONTAINER_PREFIX` | `ocv` | Docker container prefix |
| `RETENTION_DAYS` | `30` | Days to keep backups |

### Examples

```bash
# Full backup (database + configuration)
./scripts/backup.sh

# Database only
./scripts/backup.sh --db-only

# Configuration only
./scripts/backup.sh --config-only

# Keep old backups (skip cleanup)
./scripts/backup.sh --no-cleanup
```

### What Gets Backed Up

**Database:**
- SQLite: Copies .db file using SQLite backup command
- PostgreSQL: Uses pg_dumpall for full dump
- Compressed with gzip

**Configuration:**
- `.env`
- `docker-compose.yml`
- `instances/` (all instance configs)
- `backend/config/legal/`
- `nginx/conf.d/`

### Backup Location

Backups are stored in timestamped directories:
```
backups/
├── 20251230_143022/
│   ├── database.db.gz      # or database.sql.gz for PostgreSQL
│   └── config.tar.gz
├── 20251229_100000/
│   └── ...
```

---

## setup-instance.sh

Interactive script to create new OpenCitiVibes instance deployments.

### Usage

```bash
./scripts/setup-instance.sh <instance-name> <domain> [OPTIONS]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `instance-name` | Short name for the instance (e.g., montreal, paris, toronto) |
| `domain` | Domain name for the instance (e.g., ideas-montreal.ca) |

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--base-path PATH` | `/opt/opencitivibes` | Base installation path |
| `--locale LOCALE` | `en` | Default locale: `en` or `fr` |
| `--entity-type TYPE` | `city` | Entity type: city, region, organization |
| `--skip-ssl` | false | Skip SSL certificate setup |

### Examples

```bash
# Basic setup for Montreal
./scripts/setup-instance.sh montreal ideas-montreal.ca

# French instance for Paris
./scripts/setup-instance.sh paris idees-paris.fr --locale fr

# Custom base path
./scripts/setup-instance.sh toronto ideas-toronto.ca --base-path /var/www

# Organization instead of city
./scripts/setup-instance.sh acme ideas.acme.com --entity-type organization
```

### What Gets Created

```
/opt/opencitivibes-montreal/
├── .env                              # Generated with SECRET_KEY
├── docker-compose.yml                # Copied from source
├── instances/
│   └── montreal/
│       ├── platform.config.json      # Instance-specific config
│       └── images/                   # Brand assets
├── backend/
│   └── config/
│       └── legal/                    # Legal document templates
├── nginx/
│   ├── nginx.conf                    # Main nginx config
│   └── conf.d/
│       └── default.conf              # Generated from template
├── ssl/                              # SSL certificate directory
├── backups/                          # Backup directory
├── logs/                             # Log directory
└── scripts/
    ├── deploy.sh                     # Deployment script
    └── backup.sh                     # Backup script
```

### Post-Setup Steps

After running the script:

1. **Review configuration:**
   ```bash
   nano /opt/opencitivibes-montreal/.env
   nano /opt/opencitivibes-montreal/instances/montreal/platform.config.json
   ```

2. **Set up SSL certificates:**
   ```bash
   # Let's Encrypt (recommended)
   certbot certonly --standalone -d ideas-montreal.ca
   cp /etc/letsencrypt/live/ideas-montreal.ca/fullchain.pem /opt/opencitivibes-montreal/ssl/
   cp /etc/letsencrypt/live/ideas-montreal.ca/privkey.pem /opt/opencitivibes-montreal/ssl/
   ```

3. **Update IMAGE_REPOSITORY** in .env to your Docker registry

4. **Start the deployment:**
   ```bash
   cd /opt/opencitivibes-montreal
   docker compose pull
   docker compose up -d
   ```

5. **Initialize database:**
   ```bash
   docker compose exec backend python init_db.py
   ```

---

## opencitivibes.service.template

systemd service template for running OpenCitiVibes as a system service.

### Installation

```bash
# Replace placeholders and install
sed 's/{{INSTANCE_NAME}}/montreal/g; s|{{DEPLOY_PATH}}|/opt/opencitivibes-montreal|g' \
  scripts/opencitivibes.service.template > /etc/systemd/system/opencitivibes-montreal.service

# Reload systemd
systemctl daemon-reload

# Enable and start
systemctl enable opencitivibes-montreal
systemctl start opencitivibes-montreal
```

### Commands

```bash
# Start the service
systemctl start opencitivibes-montreal

# Stop the service
systemctl stop opencitivibes-montreal

# Restart (reload configuration)
systemctl restart opencitivibes-montreal

# View status
systemctl status opencitivibes-montreal

# View logs
journalctl -u opencitivibes-montreal -f
```

### Features

- Starts after Docker service
- Waits for network
- 5-minute startup timeout
- 2-minute stop timeout
- Automatic restart on failure
- Loads environment from .env file

---

## Troubleshooting

### Docker Permission Denied (Local)

```
permission denied while trying to connect to the Docker daemon socket
```

Your user needs to be in the `docker` group:

```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Log out and back in, OR use newgrp
newgrp docker

# Verify it works
docker ps
```

**Quick fix** (temporary, resets on reboot):

```bash
sudo chmod 666 /var/run/docker.sock
```

### SSH Connection Failed

```
Error: Cannot connect to user@host
```

1. Verify SSH key is configured: `ssh user@host`
2. Check firewall allows port 22
3. Ensure user exists on remote

### Docker Not Available on Remote

```
Error: Docker Compose not available on user@host
```

1. Install Docker: `curl -fsSL https://get.docker.com | sh`
2. Add user to docker group: `sudo usermod -aG docker $USER`
3. Log out and back in

### Environment File Missing

```
Error: Neither .env nor .env.example found on remote
```

1. Sync files first: `./scripts/docker-dev.sh --remote --sync up`
2. Or manually create `.env` on remote from `.env.example`

### Health Check Timeout

```
Health check timeout - deployment may have failed
```

1. Check container logs: `docker compose logs`
2. Increase timeout: `HEALTH_CHECK_TIMEOUT=120 ./scripts/deploy.sh`
3. Force deployment: `./scripts/deploy.sh --force`

---

## Service URLs

After `up`, services are available at:

| Service | Local | Remote |
|---------|-------|--------|
| Frontend | http://localhost:3000 | http://[remote-ip]:3000 |
| Backend | http://localhost:8000 | http://[remote-ip]:8000 |
| API Docs | http://localhost:8000/docs | http://[remote-ip]:8000/docs |
