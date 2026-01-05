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
claude-test/
├── backend/                    # FastAPI Backend
│   ├── routers/               # API route handlers (HTTP layer)
│   │   ├── auth_router.py    # Authentication endpoints
│   │   ├── ideas_router.py   # Ideas CRUD
│   │   ├── votes_router.py   # Voting endpoints
│   │   ├── comments_router.py # Comments endpoints
│   │   ├── categories_router.py # Category management
│   │   ├── tags_router.py    # Tag management
│   │   └── admin_router.py   # Admin operations
│   ├── services/              # Business logic layer
│   │   ├── user_service.py   # User operations
│   │   ├── idea_service.py   # Idea operations
│   │   ├── tag_service.py    # Tag operations
│   │   └── ...               # Other services
│   ├── repositories/          # Data access layer
│   │   ├── base.py           # Base repository class
│   │   ├── db_models.py      # SQLAlchemy ORM models
│   │   ├── database.py       # Database configuration
│   │   └── ...               # Specialized repositories
│   ├── models/                # Data models
│   │   ├── schemas.py        # Pydantic request/response schemas
│   │   ├── exceptions.py     # Domain exceptions
│   │   └── config.py         # App configuration
│   ├── authentication/        # Auth logic
│   │   └── auth.py           # JWT, password hashing
│   ├── helpers/               # Utility functions
│   ├── data/                  # Runtime data
│   │   └── idees_montreal.db # SQLite database
│   ├── main.py                # FastAPI app initialization
│   ├── init_db.py             # Database seeding script
│   └── requirements.txt       # Python dependencies
├── frontend/                   # Next.js Frontend
│   ├── src/
│   │   ├── app/              # Next.js 14 App Router pages
│   │   │   ├── page.tsx      # Homepage (leaderboard)
│   │   │   ├── ideas/        # Idea detail pages
│   │   │   ├── submit/       # Idea submission form
│   │   │   ├── admin/        # Admin dashboard
│   │   │   ├── tags/         # Tag pages
│   │   │   └── ...           # Other pages
│   │   ├── components/       # React components
│   │   │   ├── ui/           # Shadcn/UI components
│   │   │   ├── IdeaCard.tsx  # Idea display
│   │   │   ├── Navbar.tsx    # Navigation
│   │   │   └── ...           # Other components
│   │   ├── lib/              # Utilities
│   │   │   └── api.ts        # Centralized API client
│   │   ├── store/            # Zustand state management
│   │   │   └── authStore.ts  # Auth state
│   │   ├── types/            # TypeScript interfaces
│   │   │   └── index.ts      # All type definitions
│   │   └── i18n/             # Internationalization
│   │       ├── config.ts     # i18next configuration
│   │       └── locales/      # Translation files (en/fr)
│   ├── package.json          # Node dependencies
│   └── tailwind.config.ts    # Tailwind configuration
├── reports/                    # Code review & security audit reports
├── CLAUDE.md                   # Development guidelines for Claude Code
├── ACTIVE.md                   # Current sprint tasks
├── SPECIFICATIONS.md           # Feature specifications
├── ARCHITECTURE.md             # Technical architecture documentation
└── README.md                   # Project overview (this file)
```

## Setup Instructions

### Prerequisites
- Python 3.8+
- Node.js 18+
- npm or yarn

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
   npm install
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
   npm run dev
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
pytest

# Frontend
cd frontend
npm test
```

### Building for Production

**Backend:**
```bash
# Use a production WSGI server like Gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker
```

**Frontend:**
```bash
npm run build
npm start
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
