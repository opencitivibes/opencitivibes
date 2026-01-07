# OpenCitiVibes

**OpenCitiVibes** is an open-source citizen engagement platform that enables communities to share, discuss, and vote on ideas for improvement.

Originally developed as "Idees pour Montreal", the platform has been redesigned to be fully configurable for deployment by any city, region, or organization worldwide.

## Features

- **Idea Submission**: Citizens can submit ideas for community improvement
- **Voting System**: Upvote/downvote with quality feedback
- **Discussion**: Comments and threaded discussions
- **Moderation**: Admin panel with content moderation
- **Analytics**: Engagement metrics and reporting
- **Multi-language**: Full i18n support (English, French, extensible)
- **White-label**: Fully customizable branding

## Quick Start

```bash
# Clone repository
git clone https://github.com/your-org/opencitivibes.git

# Create new instance
./scripts/setup-instance.sh myCity ideas.mycity.gov

# Configure
nano /opt/opencitivibes-myCity/.env
nano /opt/opencitivibes-myCity/backend/config/platform.config.json

# Deploy
cd /opt/opencitivibes-myCity
docker compose up -d
```

## Documentation

- [Commissioning Guide](docs/COMMISSIONING.md) - Deploy a new instance
- [Migration Guide](docs/MIGRATION.md) - Upgrade from Montreal version
- [Configuration Reference](docs/CONFIGURATION.md) - All configuration options
- [Testing Checklist](docs/TESTING_CHECKLIST.md) - Deployment verification

## Architecture

| Component | Technology |
|-----------|------------|
| Backend | FastAPI (Python 3.13) |
| Frontend | Next.js 16 (React 19) |
| Database | SQLite / PostgreSQL |
| Auth | JWT (python-jose) |
| i18n | react-i18next |
| Styling | Tailwind CSS |

### Backend Stack
- **FastAPI**: Modern Python web framework with automatic API documentation
- **SQLAlchemy 2.0+**: ORM for database operations
- **SQLite/PostgreSQL**: Database (SQLite for dev, PostgreSQL for production)
- **Pydantic 2.10+**: Request/response validation and serialization
- **Layered Architecture**: Strict Router -> Service -> Repository pattern

### Frontend Stack
- **Next.js 16**: React framework with App Router and Server Components
- **React 19**: Modern UI library with hooks
- **TypeScript 5**: Type-safe development
- **Tailwind CSS**: Utility-first CSS framework
- **Shadcn/UI**: Accessible component library built on Radix UI
- **Zustand**: Lightweight state management
- **react-i18next**: Internationalization (French/English, extensible)

## Project Structure

```
opencitivibes/
├── backend/                    # FastAPI Backend
│   ├── routers/               # API route handlers (HTTP layer)
│   ├── services/              # Business logic layer
│   ├── repositories/          # Data access layer
│   │   ├── db_models.py      # SQLAlchemy ORM models
│   │   └── database.py       # Database configuration
│   ├── models/                # Data models
│   │   ├── schemas.py        # Pydantic request/response schemas
│   │   └── exceptions.py     # Domain exceptions
│   ├── authentication/        # Auth logic (JWT, passwords)
│   ├── helpers/               # Utility functions
│   ├── alembic/               # Database migrations
│   ├── data/                  # Runtime data (SQLite DB)
│   └── main.py                # FastAPI app initialization
├── frontend/                   # Next.js Frontend
│   ├── src/
│   │   ├── app/              # Next.js App Router pages
│   │   ├── components/       # React components
│   │   │   └── ui/           # Shadcn/UI components
│   │   ├── lib/api.ts        # Centralized API client
│   │   ├── store/            # Zustand state management
│   │   ├── types/            # TypeScript interfaces
│   │   └── i18n/             # Internationalization (en/fr)
│   ├── package.json          # Node dependencies (pnpm)
│   └── tailwind.config.ts    # Tailwind configuration
├── instances/                  # Multi-instance configurations
│   ├── montreal/             # Montreal instance
│   ├── quebec/               # Quebec instance
│   ├── calgary/              # Calgary instance
│   └── socenv/               # SocEnv instance
├── nginx/                      # Reverse proxy configuration
├── docs/                       # Documentation
├── docker-compose.yml          # Production deployment
├── docker-compose.dev.yml      # Development deployment
└── README.md                   # Project overview (this file)
```

## Setup Instructions

### Prerequisites
- Python 3.13+
- Node.js 18+
- pnpm (recommended) or npm

### Backend Setup

1. **Navigate to the backend directory:**
   ```bash
   cd backend
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   ```

3. **Activate the virtual environment:**
   - Windows (Git Bash/MINGW):
     ```bash
     source venv/Scripts/activate
     ```
   - macOS/Linux:
     ```bash
     source venv/bin/activate
     ```

4. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

5. **Create environment file:**
   ```bash
   cp .env.example .env
   ```

   Edit `.env` and update the `SECRET_KEY` for production use:
   ```
   SECRET_KEY=your-very-secure-secret-key-here
   ```

6. **Initialize the database:**
   ```bash
   python init_db.py
   ```

   This will create:
   - Default categories (Transportation, Environment, Culture, etc.)
   - Admin user (email: `admin@idees-montreal.ca`, password: `admin123`)

   **⚠️ IMPORTANT**: Change the admin password in production!

7. **Run the backend server:**
   ```bash
   uvicorn main:app --reload --port 8000
   ```

   The API will be available at `http://localhost:8000`
   - API docs: `http://localhost:8000/docs`
   - Health check: `http://localhost:8000/api/health`

### Frontend Setup

1. **Navigate to the frontend directory (in a new terminal):**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   pnpm install
   ```

3. **Create environment file:**
   ```bash
   cp .env.example .env.local
   ```

   The default configuration should work:
   ```
   NEXT_PUBLIC_API_URL=http://localhost:8000/api
   ```

4. **Run the development server:**
   ```bash
   pnpm dev
   ```

   The application will be available at `http://localhost:3000`

## Usage

### For Regular Users

1. **Browse Ideas**: Visit the homepage to see the leaderboard of approved ideas
2. **Filter by Category**: Use the dropdown to filter ideas by category
3. **Sign Up**: Click "Sign Up" to create an account
4. **Sign In**: Click "Sign In" to log into your account
5. **Submit an Idea**: After signing in, click "Submit an Idea" to propose a new idea
6. **Vote**: Click the thumbs up/down buttons on approved ideas
7. **View Your Ideas**: Click "My Ideas" to see your submitted ideas and their status

### For Administrators

1. **Sign In**: Use the admin credentials:
   - Email: `admin@idees-montreal.ca`
   - Password: `admin123` (change this!)

2. **Access Admin Panel**: Click "Admin" in the navigation

3. **Moderate Ideas**:
   - Review pending ideas
   - Click "Moderate" on an idea
   - Add an optional admin comment
   - Click "Approve" or "Reject"

4. **Moderate Comments**: View and moderate user comments (future feature)

5. **Manage Roles**: Assign admin privileges to other users (future feature)

## API Documentation

Full API documentation is available when the backend is running:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

The API follows RESTful principles with endpoints for:
- Authentication (register, login, user profile)
- Ideas (create, read, update, delete, vote, comment)
- Categories (list, filter)
- Admin operations (moderate ideas/comments, manage roles)

## Development

### Running Tests
```bash
# Backend
cd backend
uv run pytest

# Frontend
cd frontend
pnpm test
```

### Building for Production

**Backend:**
```bash
# Use a production WSGI server like Gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker
```

**Frontend:**
```bash
pnpm build
pnpm start
```

### Docker Deployment (Recommended)

The easiest way to deploy is with Docker:

```bash
# Development (with hot reload)
docker compose --profile dev up -d

# Production
docker compose --profile prod up -d
```

Docker profiles:
- `dev` - SQLite + Mailpit (email testing) + hot reload
- `staging` - SQLite + Postfix (real email)
- `prod` - PostgreSQL + Postfix + optimized builds

### Multi-Instance Deployment

Each instance has its own configuration in `instances/<name>/`:

```bash
# Switch to a different instance
./scripts/switch-instance.sh quebec

# Deploy with instance config
PLATFORM_CONFIG_PATH=./instances/quebec/platform.config.json docker compose up -d
```

## Environment Variables

### Backend (.env)
- `DATABASE_URL`: Database connection string
- `SECRET_KEY`: JWT secret key (change in production!)
- `ALGORITHM`: JWT algorithm (default: HS256)
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Token expiration time

### SECRET_KEY Loading Behavior

The `SECRET_KEY` is **required** for the application to start. How it's loaded depends on the context:

| Context | `.env` Auto-Loaded? | SECRET_KEY Source |
|---------|---------------------|-------------------|
| Development (`uvicorn`) | Yes | `.env` file |
| pytest | No | `conftest.py` sets `os.environ["SECRET_KEY"]` |
| CI (`CI=true`) | No | Must be set in environment |
| Migration scripts | Yes | `.env` file or explicit env var |

**Notes:**
- In development, simply create a `.env` file with `SECRET_KEY=your-key`
- For migrations, if `.env` exists, you don't need to pass `SECRET_KEY=` explicitly
- In CI/production, always set `SECRET_KEY` via environment variables

### Frontend (.env.local)
- `NEXT_PUBLIC_API_URL`: Backend API URL

## License

MIT License - see [LICENSE](LICENSE) file.

## Support

For issues, questions, or contributions, please open an issue on the project repository.

## Credits

Originally built for the Montreal community, now available for communities worldwide.
