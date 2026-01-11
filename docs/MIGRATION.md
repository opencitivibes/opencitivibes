# Migrating from "Idees pour Montreal" to OpenCitiVibes

This guide covers migrating an existing Montreal-specific deployment to the new configurable OpenCitiVibes architecture.

## Overview

The migration involves:
1. Backing up existing data
2. Updating configuration files
3. Renaming Docker resources
4. Applying new configuration
5. Verifying the migration

## Pre-Migration Checklist

- [ ] Current deployment is stable
- [ ] Full database backup completed
- [ ] Configuration files backed up
- [ ] Downtime window scheduled (15-30 min)

## Migration Steps

### Step 1: Backup Everything

```bash
cd /opt/idees-montreal

# Backup database
cp data/idees_montreal.db data/idees_montreal.db.backup.$(date +%Y%m%d)

# Backup configuration
tar -czf config_backup_$(date +%Y%m%d).tar.gz .env docker-compose.yml nginx/
```

### Step 2: Stop Current Deployment

```bash
docker compose down
```

### Step 3: Create Platform Configuration

Create `backend/config/platform.config.json`:

```json
{
  "platform": {
    "name": "OpenCitiVibes",
    "version": "1.0.0"
  },
  "instance": {
    "name": {
      "en": "Ideas for Montreal",
      "fr": "Idees pour Montreal"
    },
    "entity": {
      "type": "city",
      "name": {
        "en": "Montreal",
        "fr": "Montreal"
      },
      "region": {
        "en": "Quebec",
        "fr": "Quebec"
      },
      "country": {
        "en": "Canada",
        "fr": "Canada"
      }
    },
    "location": {
      "display": {
        "en": "Montreal, Quebec",
        "fr": "Montreal, Quebec"
      },
      "timezone": "America/Montreal"
    }
  },
  "contact": {
    "email": "contact@idees-montreal.ca"
  },
  "legal": {
    "jurisdiction": {
      "en": "Quebec and Canada",
      "fr": "Quebec et Canada"
    },
    "courts": {
      "en": "competent courts of Quebec",
      "fr": "tribunaux competents du Quebec"
    },
    "privacy_authority": {
      "name": {
        "en": "Commission d'acces a l'information du Quebec",
        "fr": "Commission d'acces a l'information du Quebec"
      },
      "acronym": "CAI"
    }
  },
  "branding": {
    "primary_color": "#0066CC",
    "secondary_color": "#003366",
    "hero_image": "/images/hero/montreal-skyline.jpg"
  },
  "localization": {
    "default_locale": "fr",
    "supported_locales": ["fr", "en"]
  }
}
```

### Step 4: Update .env File

```bash
# Add new variables (keep existing ones)
echo "" >> .env
echo "# OpenCitiVibes Configuration" >> .env
echo "COMPOSE_PROJECT_NAME=idees-montreal" >> .env
echo "CONTAINER_PREFIX=idees-mtl" >> .env
echo "PLATFORM_CONFIG_PATH=./config/platform.config.json" >> .env
```

### Step 5: Update docker-compose.yml

Replace with new template from `docker-compose.yml`.

### Step 6: Rename Database (Optional)

```bash
mv data/idees_montreal.db data/opencitivibes.db
# Update DATABASE_URL in .env accordingly
```

### Step 7: Deploy New Version

```bash
docker compose pull
docker compose up -d
```

### Step 8: Verify Migration

```bash
# Check services
docker compose ps

# Check logs
docker compose logs backend | tail -20

# Test API
curl http://localhost:8000/api/health

# Test frontend
curl http://localhost:3000
```

### Step 9: Run Database Migration (if needed)

```bash
docker compose exec backend alembic upgrade head
```

## Rollback Plan

If migration fails:

```bash
# Stop new deployment
docker compose down

# Restore backup
cp data/idees_montreal.db.backup.* data/idees_montreal.db
tar -xzf config_backup_*.tar.gz

# Restore old docker-compose
# (keep backup of old docker-compose.yml)

# Restart old deployment
docker compose up -d
```

## Post-Migration Checklist

- [ ] Update DNS if domain changed
- [ ] Update SSL certificates if needed
- [ ] Notify users of any visible changes
- [ ] Monitor logs for errors
- [ ] Update CI/CD pipelines

## Data Migration Details

### Database Schema

The OpenCitiVibes database schema is identical to the existing schema. No data migration is required for:
- Users
- Ideas
- Comments
- Votes
- Categories
- Tags

### Configuration Migration

| Old Location | New Location | Notes |
|--------------|--------------|-------|
| `.env` | `.env` + `platform.config.json` | Split static vs dynamic config |
| Hardcoded in code | `platform.config.json` | All instance-specific values |
| N/A | `legal.config.json` | Legal content configuration |

### Breaking Changes

1. **API Title**: Changed from "Idees pour Montreal API" to "OpenCitiVibes API"
   - Impact: API documentation display only

2. **Container Names**: Now use configurable prefix
   - Impact: Update any scripts referencing old container names

3. **Config Endpoint**: New `/api/config` endpoint
   - Impact: Frontend will use this for dynamic configuration

## Verification Tests

After migration, verify:

```bash
# 1. API health
curl -s http://localhost:8000/api/health | jq

# 2. Config endpoint
curl -s http://localhost:8000/api/config | jq

# 3. Ideas endpoint
curl -s http://localhost:8000/api/ideas | jq '.total'

# 4. Frontend loads
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000

# 5. Static assets
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/images/hero/montreal-skyline.jpg
```

## Database Schema Migrations (Alembic)

This section covers applying Alembic migrations to the production PostgreSQL database after new features are deployed via GitHub Actions.

### Production Environment

| Component | Value |
|-----------|-------|
| VPS Host | `your-domain.example.com` |
| SSH User | `ubuntu` |
| SSH Key | `~/.ssh/your_deploy_key` |
| Backend Container | `${CONTAINER_PREFIX}-backend` |
| Database Container | `${CONTAINER_PREFIX}-postgres` |
| Database | PostgreSQL 16 |

> **Note**: Replace placeholders with your actual values. See your `.env` file for `CONTAINER_PREFIX`.

### Deployment Flow

1. **Push to main** → Triggers CI workflow
2. **CI passes** → Triggers Build and Deploy workflow
3. **Images built** → Pushed to GHCR (`ghcr.io/opencitivibes/opencitivibes/backend:latest`)
4. **VPS pulls images** → Containers restarted automatically
5. **Manual step** → Run Alembic migration

### Running Migrations on Production

#### Step 1: Check current migration status

```bash
ssh -i ~/.ssh/your_deploy_key ubuntu@your-domain.example.com \
  "docker exec idees-mtl-backend alembic current"
```

#### Step 2: View pending migrations

```bash
ssh -i ~/.ssh/your_deploy_key ubuntu@your-domain.example.com \
  "docker exec idees-mtl-backend alembic history | head -20"
```

#### Step 3: Apply migrations

```bash
ssh -i ~/.ssh/your_deploy_key ubuntu@your-domain.example.com \
  "docker exec idees-mtl-backend alembic upgrade head"
```

#### Step 4: Verify migration applied

```bash
ssh -i ~/.ssh/your_deploy_key ubuntu@your-domain.example.com \
  "docker exec idees-mtl-backend alembic current"
```

Should show: `<revision_id> (head)`

### One-liner for full deployment + migration

```bash
# Wait for GitHub Actions to complete, then:
ssh -i ~/.ssh/your_deploy_key ubuntu@your-domain.example.com \
  "docker exec idees-mtl-backend alembic upgrade head"
```

### Rolling back a migration

```bash
# Rollback one migration
ssh -i ~/.ssh/your_deploy_key ubuntu@your-domain.example.com \
  "docker exec idees-mtl-backend alembic downgrade -1"

# Rollback to specific revision
ssh -i ~/.ssh/your_deploy_key ubuntu@your-domain.example.com \
  "docker exec idees-mtl-backend alembic downgrade <revision_id>"
```

### Checking container status

```bash
ssh -i ~/.ssh/your_deploy_key ubuntu@your-domain.example.com \
  "docker ps --format 'table {{.Names}}\t{{.Status}}'"
```

Expected output:
```
NAMES                STATUS
idees-mtl-backend    Up X minutes (healthy)
idees-mtl-frontend   Up X minutes (healthy)
idees-mtl-nginx      Up X minutes (healthy)
idees-mtl-postgres   Up X hours (healthy)
idees-mtl-postfix    Up X hours (healthy)
idees-mtl-ntfy       Up X hours (healthy)
```

### Creating new migrations locally

```bash
cd backend

# Auto-generate from model changes
uv run alembic revision --autogenerate -m "description of changes"

# Or create empty migration
uv run alembic revision -m "description of changes"
```

**Important**: After creating a migration, verify the `down_revision` points to the current head to avoid branching conflicts.

### Troubleshooting migrations

#### Migration branch conflict

If you see "Multiple heads" error:
```bash
# Check for branches
uv run alembic heads

# Merge branches (locally)
uv run alembic merge -m "merge heads" <rev1> <rev2>
```

#### Migration fails on production

```bash
# Check backend logs
ssh -i ~/.ssh/your_deploy_key ubuntu@your-domain.example.com \
  "docker logs idees-mtl-backend --tail 50"

# Connect to database directly
ssh -i ~/.ssh/your_deploy_key ubuntu@your-domain.example.com \
  "docker exec -it idees-mtl-postgres psql -U postgres -d opencitivibes"
```

## Support

If you encounter issues during migration:

1. Check the [Troubleshooting Guide](COMMISSIONING.md#troubleshooting)
2. Review container logs: `docker compose logs`
3. Verify configuration: `python -m json.tool backend/config/platform.config.json`
4. Open an issue with:
   - Migration step where failure occurred
   - Error messages from logs
   - Current and target versions
