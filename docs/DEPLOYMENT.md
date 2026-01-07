# CI/CD Deployment Guide

This guide explains the automated deployment workflow using GitHub Actions.

## Overview

OpenCitiVibes uses a **safe-by-default** deployment strategy:

| Environment | Trigger | Approval |
|-------------|---------|----------|
| **Staging** | Automatic on push to `main` | None (auto-deploys after CI passes) |
| **Production** | Manual only | Requires explicit action |

This design ensures production is never accidentally updated - it always requires intentional human action.

## Workflow: Build and Deploy

**File:** `.github/workflows/deploy.yml`

### Triggers

```yaml
on:
  # After CI passes on main branch
  workflow_run:
    workflows: ["CI"]
    types: [completed]
    branches: [main]

  # Manual trigger with environment selection
  workflow_dispatch:
    inputs:
      environment:
        type: choice
        options: [staging, production]
```

### Jobs Flow

```
┌─────────────────────────────────────────────────────────────┐
│                     Push to main                            │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    CI Workflow                              │
│   (lint, type-check, tests, security scans)                 │
└─────────────────────────────────────────────────────────────┘
                           │
                     CI passes?
                      │      │
                     Yes     No → Stop
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              Build and Deploy Workflow                      │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐    ┌─────────────────┐                │
│  │  build-backend  │    │ build-frontend  │  (parallel)    │
│  └────────┬────────┘    └────────┬────────┘                │
│           │                      │                          │
│           └──────────┬───────────┘                          │
│                      ▼                                      │
│           ┌─────────────────┐                               │
│           │ deploy-staging  │  ← Auto (main branch)         │
│           └─────────────────┘                               │
│                                                             │
│           ┌─────────────────┐                               │
│           │deploy-production│  ← Manual only                │
│           └─────────────────┘                               │
└─────────────────────────────────────────────────────────────┘
```

## Deploying to Staging

Staging deploys automatically when:
1. Code is pushed to `main`
2. CI workflow completes successfully

```bash
# Just push to main - staging deploys automatically
git push origin main
```

The workflow:
1. Waits for CI to pass
2. Builds Docker images (backend + frontend)
3. Pushes images to GitHub Container Registry
4. SSHs to staging server
5. Pulls latest images
6. Restarts services with `--profile staging`
7. Verifies health checks

## Deploying to Production

Production **never** auto-deploys. You must manually trigger it.

### Option 1: GitHub UI

1. Go to **Actions** → **Build and Deploy**
2. Click **Run workflow** (top right)
3. Select `production` from the dropdown
4. Click **Run workflow**

### Option 2: GitHub CLI

```bash
gh workflow run deploy.yml -f environment=production
```

### Option 3: After Staging Verification

Common workflow:
1. Push to `main` → staging auto-deploys
2. Test on staging
3. If OK, manually trigger production deploy

```bash
# Check staging is healthy
curl -s https://staging.yourdomain.com/api/health

# Deploy to production
gh workflow run deploy.yml -f environment=production

# Monitor deployment
gh run watch
```

## Environments

GitHub Environments provide:
- **Protection rules** - require reviewers, wait timers
- **Secrets** - environment-specific credentials
- **Deployment history** - track what's deployed where

### Staging Environment

| Secret | Description |
|--------|-------------|
| `STAGING_HOST` | Staging server IP/hostname |
| `STAGING_USER` | SSH username |
| `STAGING_SSH_KEY` | SSH private key |
| `STAGING_DEPLOY_PATH` | Path to docker-compose.yml |

### Production Environment

| Secret | Description |
|--------|-------------|
| `PRODUCTION_HOST` | Production server IP/hostname |
| `PRODUCTION_USER` | SSH username |
| `PRODUCTION_SSH_KEY` | SSH private key |
| `PRODUCTION_DEPLOY_PATH` | Path to docker-compose.yml |

### Shared Secrets (repository level)

| Secret | Description |
|--------|-------------|
| `NEXT_PUBLIC_API_URL` | Backend API URL |
| `NEXT_PUBLIC_SITE_URL` | Frontend URL |
| `NEXT_PUBLIC_SENTRY_DSN` | Sentry DSN for error tracking |

## Docker Compose Profiles

Each environment uses a specific profile:

| Profile | Database | Email | Use Case |
|---------|----------|-------|----------|
| `staging` | SQLite | Postfix | Pre-production testing |
| `prod` | PostgreSQL | Postfix | Production |

```bash
# Staging deployment runs:
docker compose --profile staging up -d

# Production deployment runs:
docker compose --profile prod up -d
```

## Image Tagging

Images are tagged with:
- Git commit SHA (e.g., `ghcr.io/org/repo/backend:abc1234`)
- `latest` on main branch

```bash
# Pull specific version
docker pull ghcr.io/opencitivibes/opencitivibes/backend:abc1234

# Pull latest
docker pull ghcr.io/opencitivibes/opencitivibes/backend:latest
```

## Monitoring Deployments

### GitHub Actions UI

1. Go to **Actions** tab
2. Click on the workflow run
3. View logs for each job

### GitHub CLI

```bash
# List recent runs
gh run list --workflow=deploy.yml

# Watch live
gh run watch

# View specific run
gh run view <run-id>

# View logs
gh run view <run-id> --log
```

### Server-side

```bash
# Check container status
docker compose --profile staging ps

# View logs
docker compose --profile staging logs -f backend

# Check health
curl -s http://localhost:8000/api/health
```

## Database Migrations

After deploying new code that includes schema changes, you must run Alembic migrations to update the database.

### Running Migrations

```bash
# Via SSH to the server
ssh user@ssh.yourdomain.com

# Run migrations on the backend container
docker exec <container-prefix>-backend alembic upgrade head

# Example for production (idees-mtl prefix)
docker exec idees-mtl-backend alembic upgrade head
```

### Checking Migration Status

```bash
# View current migration revision
docker exec idees-mtl-backend alembic current

# View migration history
docker exec idees-mtl-backend alembic history

# Check pending migrations
docker exec idees-mtl-backend alembic heads
```

### Migration Best Practices

1. **Always backup before migrating** - The deploy workflow runs `./scripts/backup.sh` automatically for production
2. **Test migrations on staging first** - Staging uses SQLite, production uses PostgreSQL
3. **Review migration files** - Check `backend/alembic/versions/` for new migrations before deploying
4. **Migrations are not automatic** - The CI/CD workflow deploys containers but does NOT run migrations

### Troubleshooting Migrations

```bash
# If migration fails, check the error
docker exec idees-mtl-backend alembic upgrade head 2>&1

# View detailed migration info
docker exec idees-mtl-backend alembic show head

# Downgrade if needed (use with caution!)
docker exec idees-mtl-backend alembic downgrade -1
```

### Common Migration Scenarios

**New column added:**
```bash
# Just run upgrade - Alembic handles it
docker exec idees-mtl-backend alembic upgrade head
```

**New table added:**
```bash
# Same process
docker exec idees-mtl-backend alembic upgrade head
```

**Data migration needed:**
```bash
# Check migration file for any manual steps
# Some migrations may include data transformations
docker exec idees-mtl-backend alembic upgrade head
```

## Rollback

### Quick Rollback

Pull and deploy a previous image tag:

```bash
# On the server
cd /path/to/deployment

# Find previous SHA from git log or GitHub
git log --oneline -10

# Pull specific version
docker compose pull backend:abc1234 frontend:abc1234

# Restart
docker compose --profile prod up -d
```

### Via GitHub Actions

Re-run a previous successful deployment:

1. Go to **Actions** → **Build and Deploy**
2. Find the last known good run
3. Click **Re-run all jobs**

## Adding Protection Rules (Optional)

For additional safety, configure environment protection:

1. Go to **Settings** → **Environments** → **production**
2. Enable **Required reviewers**
3. Add team members who must approve
4. Optionally add **Wait timer** (e.g., 5 minutes)

With protection rules, production deploys will:
1. Wait for approval from designated reviewers
2. Show pending status in GitHub UI
3. Only proceed after approval

## Troubleshooting

### Deployment Failed

```bash
# Check GitHub Actions logs
gh run view <run-id> --log-failed

# SSH to server and check
ssh user@server
docker compose --profile staging logs backend
docker compose --profile staging ps
```

### Health Check Failed

The workflow checks for "unhealthy" containers after deploy:

```bash
# On server
docker compose --profile staging ps

# Check specific container
docker inspect --format='{{.State.Health}}' container-name

# View health check logs
docker inspect --format='{{json .State.Health}}' container-name | jq
```

### SSH Connection Failed

1. Verify secrets are set correctly in GitHub
2. Check SSH key has correct permissions on server
3. Verify server firewall allows GitHub Actions IPs

```bash
# Test SSH manually (with the private key)
ssh -i /path/to/key user@server
```

**Cloudflare Users:** If your domain is behind Cloudflare proxy, SSH connections will fail because Cloudflare doesn't proxy port 22. Solutions:

1. **Use direct IP** - Set `PRODUCTION_HOST` / `STAGING_HOST` to the server IP
2. **Create SSH subdomain** - Add `ssh.yourdomain.com` with **DNS only** (grey cloud) in Cloudflare
3. **Use the SSH subdomain** - Set secrets to `ssh.yourdomain.com`

```bash
# Verify DNS-only (should return your server IP, not Cloudflare)
dig +short ssh.yourdomain.com
# Should return: 51.161.10.37 (your server IP)

# NOT a Cloudflare IP like: 104.21.74.4
```

## Manual Deployment Script (deploy.sh)

For server-side deployments without GitHub Actions, use the `deploy.sh` script directly on the VPS.

**File:** `scripts/deploy.sh`

### When to Use

| Scenario | Use |
|----------|-----|
| Automated CI/CD | GitHub Actions (preferred) |
| Manual server update | `deploy.sh` |
| Emergency hotfix on server | `deploy.sh` |
| Debugging deployment issues | `deploy.sh` with `--force` |
| No GitHub Actions access | `deploy.sh` |

### Usage

```bash
# SSH to the server
ssh user@ssh.yourdomain.com
cd /path/to/deployment

# Normal deployment (with backup and health checks)
./scripts/deploy.sh

# Deploy without pre-deployment backup
./scripts/deploy.sh --no-backup

# Force deploy (skip health checks)
./scripts/deploy.sh --force

# Show help
./scripts/deploy.sh --help
```

### What It Does

1. **Checks requirements** - Verifies `.env`, `docker-compose.yml`, Docker installed
2. **Creates backup** - Runs `scripts/backup.sh` (unless `--no-backup`)
3. **Stores rollback state** - Saves current image digests to `/tmp/`
4. **Pulls latest images** - `docker compose pull`
5. **Generates nginx configs** - Processes templates with `envsubst`:
   - `nginx/conf.d/default.conf.template` → `default.conf`
   - `nginx/conf.d/ntfy.conf.template` → `ntfy.conf`
6. **Deploys containers** - `docker compose up -d --remove-orphans`
7. **Health checks** - Waits for all containers to be healthy (60s timeout)
8. **Verifies deployment** - Confirms no unhealthy containers
9. **Cleans up** - Prunes old Docker resources

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DEPLOY_PATH` | Current dir | Path to deployment directory |
| `COMPOSE_PROJECT_NAME` | `opencitivibes` | Docker Compose project name |
| `BACKUP_BEFORE_DEPLOY` | `true` | Run backup before deploying |
| `HEALTH_CHECK_TIMEOUT` | `60` | Seconds to wait for health checks |

### Example Workflow

```bash
# 1. SSH to server
ssh -i ~/.ssh/key ubuntu@ssh.yourdomain.com

# 2. Navigate to deployment
cd /opt/opencitivibes

# 3. Pull latest code (if using git on server)
git pull origin main

# 4. Deploy
./scripts/deploy.sh

# 5. Verify
docker compose ps
curl -s http://localhost:8000/api/health
```

### Nginx Template Processing

The script automatically generates nginx configs from templates using variables from `.env`:

```bash
# Variables substituted:
# ${DOMAIN} - e.g., "ideespourmontreal.opencitivibes.ovh"
# ${CONTAINER_PREFIX} - e.g., "idees-mtl"

# Templates:
nginx/conf.d/default.conf.template  →  default.conf
nginx/conf.d/ntfy.conf.template     →  ntfy.conf
```

### Troubleshooting

**Health check timeout:**
```bash
# Check container status
docker compose ps

# View logs for unhealthy container
docker compose logs backend

# Force deploy anyway
./scripts/deploy.sh --force
```

**Rollback info:**
```bash
# Script shows rollback instructions if deployment fails
./scripts/deploy.sh --rollback
```

**Missing template:**
```bash
# If templates don't exist, copy from repo
curl -sL https://raw.githubusercontent.com/opencitivibes/opencitivibes/main/nginx/conf.d/default.conf.template \
  -o nginx/conf.d/default.conf.template
curl -sL https://raw.githubusercontent.com/opencitivibes/opencitivibes/main/nginx/conf.d/ntfy.conf.template \
  -o nginx/conf.d/ntfy.conf.template
```

## Related Documentation

- [Cloudflare Guide](CLOUDFLARE.md) - CDN, caching, and security settings
- [Commissioning Guide](COMMISSIONING.md) - Setting up new instances
- [Configuration Reference](CONFIGURATION.md) - All configuration options
- [Testing Checklist](TESTING_CHECKLIST.md) - Pre-deployment verification
