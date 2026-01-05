# Backend Scripts

## generate_test_data.py

Generate test SQLite databases with realistic fake data for development, testing, and performance benchmarking.

### Features

- Multiple user types (global admins, category admins, regular users)
- Ideas with various statuses (approved, pending, rejected)
- Tags and tag associations
- Votes with quality selections (upvotes/downvotes)
- Comments (including flagged and hidden) with likes
- Content moderation data (flags, penalties, appeals)
- **Law 25 compliance data** (policy versions, consent logs)
- **Instance-aware language distribution** (FR/EN/ES based on config)
- French-Canadian names and content
- Date distribution for analytics testing
- **FTS5 full-text search** setup with triggers (no separate migration needed)

### Dataset Sizes

| Size | Users | Ideas | Votes | Comments | DB Size | Gen. Time |
|------|-------|-------|-------|----------|---------|-----------|
| `small` | 108 | 500 | ~8K | ~2.5K | ~2 MB | ~10 sec |
| `medium` | 1,015 | 5,000 | ~150K | ~50K | ~50 MB | ~2 min |
| `large` | 10,030 | 50,000 | ~3M | ~750K | ~500 MB | ~20 min |

### Generated Database Files

Each size creates its own database file:

| Size | Database File |
|------|---------------|
| `small` | `data/idees_montreal_test_small.db` |
| `medium` | `data/idees_montreal_test_medium.db` |
| `large` | `data/idees_montreal_test_large.db` |

This allows you to pre-generate all sizes and switch between them instantly.

### Usage

```bash
cd backend

# Generate SMALL dataset (default) - for quick development
uv run python scripts/generate_test_data.py

# Generate MEDIUM dataset - realistic small-scale deployment
uv run python scripts/generate_test_data.py --size medium

# Generate LARGE dataset - city-scale stress testing
uv run python scripts/generate_test_data.py --size large

# Generate all sizes at once
uv run python scripts/generate_test_data.py --size small && \
uv run python scripts/generate_test_data.py --size medium && \
uv run python scripts/generate_test_data.py --size large
```

### Instance-Specific Generation

Generate databases with language distribution matching each platform instance:

```bash
cd backend

# Montreal instance (70% FR, 30% EN)
PLATFORM_CONFIG_PATH=/home/matt/projects/IdeesPourMontreal/instances/montreal/platform.config.json \
  uv run python scripts/generate_test_data.py --size small -o data/idees_montreal_test_small.db

# Quebec instance (50% FR, 35% EN, 15% ES)
PLATFORM_CONFIG_PATH=/home/matt/projects/IdeesPourMontreal/instances/quebec/platform.config.json \
  uv run python scripts/generate_test_data.py --size small -o data/opencitivibes_quebec_test_small.db

# Calgary instance (100% EN)
PLATFORM_CONFIG_PATH=/home/matt/projects/IdeesPourMontreal/instances/calgary/platform.config.json \
  uv run python scripts/generate_test_data.py --size small -o data/opencitivibes_calgary_test_small.db

# SOCENV/CDN-NDG instance (65% FR, 35% EN)
PLATFORM_CONFIG_PATH=/home/matt/projects/IdeesPourMontreal/instances/socenv/platform.config.json \
  uv run python scripts/generate_test_data.py --size small -o data/opencitivibes_socenv_test_small.db
```

**Language Distribution by Instance:**

| Instance | French | English | Spanish |
|----------|--------|---------|---------|
| Montreal | 70% | 30% | - |
| Quebec | 50% | 35% | 15% |
| Calgary | - | 100% | - |
| SOCENV | 65% | 35% | - |

### Running the Backend with Test Database

```bash
cd backend

# Run with SMALL test database (generic)
DATABASE_URL=sqlite:///./data/opencitivibes_test_small.db uv run uvicorn main:app --reload

# Run with MEDIUM test database
DATABASE_URL=sqlite:///./data/opencitivibes_test_medium.db uv run uvicorn main:app --reload

# Run with LARGE test database
DATABASE_URL=sqlite:///./data/opencitivibes_test_large.db uv run uvicorn main:app --reload
```

### Running with Instance-Specific Test Database

```bash
cd backend

# Montreal instance
PLATFORM_CONFIG_PATH=/home/matt/projects/IdeesPourMontreal/instances/montreal/platform.config.json \
  DATABASE_URL=sqlite:///./data/idees_montreal_test_small.db \
  uv run uvicorn main:app --reload

# Quebec instance
PLATFORM_CONFIG_PATH=/home/matt/projects/IdeesPourMontreal/instances/quebec/platform.config.json \
  DATABASE_URL=sqlite:///./data/opencitivibes_quebec_test_small.db \
  uv run uvicorn main:app --reload

# Calgary instance
PLATFORM_CONFIG_PATH=/home/matt/projects/IdeesPourMontreal/instances/calgary/platform.config.json \
  DATABASE_URL=sqlite:///./data/opencitivibes_calgary_test_small.db \
  uv run uvicorn main:app --reload

# SOCENV instance
PLATFORM_CONFIG_PATH=/home/matt/projects/IdeesPourMontreal/instances/socenv/platform.config.json \
  DATABASE_URL=sqlite:///./data/opencitivibes_socenv_test_small.db \
  uv run uvicorn main:app --reload
```

### Using Environment Variables

```bash
cd backend

# Option 1: Export for session
export DATABASE_URL=sqlite:///./data/idees_montreal_test_medium.db
uv run uvicorn main:app --reload

# Option 2: Create a .env.test file
echo "DATABASE_URL=sqlite:///./data/idees_montreal_test_medium.db" > .env.test

# Then copy when needed
cp .env.test .env
uv run uvicorn main:app --reload
```

### Switching Back to Production Database

```bash
cd backend

# Unset the environment variable
unset DATABASE_URL

# Or run without the variable (uses default from .env)
uv run uvicorn main:app --reload
```

### Test User Credentials

After generating data, credentials are documented in `claude-docs/testing/TEST_USERS.md`.

**Quick reference (same for all sizes):**

| Role | Email | Password |
|------|-------|----------|
| Global Admin | `admin1@idees-montreal.ca` | `Admin123!` |
| Category Admin | `catadmin1@idees-montreal.ca` | `CatAdmin123!` |
| Regular User | `firstname.lastname@example.com` | `User123!` |

### Output Files

| File | Description |
|------|-------------|
| `data/idees_montreal_test_small.db` | Small SQLite test database |
| `data/idees_montreal_test_medium.db` | Medium SQLite test database |
| `data/idees_montreal_test_large.db` | Large SQLite test database |
| `claude-docs/testing/TEST_USERS.md` | User credentials documentation |

### Example Workflow

```bash
# 1. Generate all test databases (one-time setup)
cd backend
uv run python scripts/generate_test_data.py --size small
uv run python scripts/generate_test_data.py --size medium

# 2. Start backend with desired test database
DATABASE_URL=sqlite:///./data/idees_montreal_test_medium.db uv run uvicorn main:app --reload

# 3. Start frontend (in another terminal)
cd frontend
pnpm dev

# 4. Login with test credentials
# Email: admin1@idees-montreal.ca
# Password: Admin123!

# 5. Switch to different size (restart backend)
# Ctrl+C to stop, then:
DATABASE_URL=sqlite:///./data/idees_montreal_test_small.db uv run uvicorn main:app --reload
```

### Testing Scenarios

#### Performance Testing
```bash
# Generate large dataset (if not already done)
uv run python scripts/generate_test_data.py --size large

# Run with large database
DATABASE_URL=sqlite:///./data/idees_montreal_test_large.db uv run uvicorn main:app --reload

# Test pagination with large offsets
curl "http://localhost:8000/api/ideas?skip=25000&limit=20"

# Test leaderboard with many votes
curl "http://localhost:8000/api/ideas/leaderboard?limit=50"
```

#### Moderation Testing
```bash
# Run with medium database (has moderation data)
DATABASE_URL=sqlite:///./data/idees_montreal_test_medium.db uv run uvicorn main:app --reload

# Login as admin and check moderation queue
# The dataset includes flagged content, penalties, and appeals
```

#### Analytics Testing
```bash
# Data is spread over 1-3 years depending on dataset size
# Perfect for testing trend charts and category analytics
curl "http://localhost:8000/api/analytics/overview"
curl "http://localhost:8000/api/analytics/trends?granularity=month"
```

### Shell Aliases (Optional)

Add to your `~/.bashrc` or `~/.zshrc`:

```bash
# Idees Montreal test databases
alias idees-small='cd /path/to/backend && DATABASE_URL=sqlite:///./data/idees_montreal_test_small.db uv run uvicorn main:app --reload'
alias idees-medium='cd /path/to/backend && DATABASE_URL=sqlite:///./data/idees_montreal_test_medium.db uv run uvicorn main:app --reload'
alias idees-large='cd /path/to/backend && DATABASE_URL=sqlite:///./data/idees_montreal_test_large.db uv run uvicorn main:app --reload'
alias idees-prod='cd /path/to/backend && uv run uvicorn main:app --reload'
```

### Notes

- Each size has its **own database file** - they don't overwrite each other
- You can pre-generate all sizes and switch instantly
- Production database (`data/idees_montreal.db`) is never modified
- Passwords are hashed with bcrypt (same as production)
- All dates are timezone-aware (UTC)
- Re-running with the same size **replaces** that size's database
- **FTS5 search is fully configured** - includes virtual table and sync triggers
- No need to run Alembic migrations for test databases
