# Quick Start Guide

Get "Idées pour Montréal" running in 5 minutes!

## Prerequisites

Make sure you have installed:
- Python 3.8 or higher
- Node.js 18 or higher

## Step 1: Backend Setup (Terminal 1)

```bash
# Navigate to backend
cd backend

# Create and activate virtual environment
python -m venv venv
source venv/Scripts/activate  # On Windows Git Bash
# source venv/bin/activate     # On macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Initialize database with default data
python init_db.py

# Start the backend server
uvicorn main:app --reload --port 8000
```

✅ Backend running at http://localhost:8000

## Step 2: Frontend Setup (Terminal 2)

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Start the development server
npm run dev
```

✅ Frontend running at http://localhost:3000

## Step 3: Try It Out!

### As a Regular User:
1. Open http://localhost:3000
2. Browse the leaderboard (currently empty)
3. Click "Sign Up" to create an account
4. Submit your first idea!
5. Vote on ideas (after they're approved)

### As an Administrator:
1. Sign in with:
   - **Email**: admin@idees-montreal.ca
   - **Password**: admin123
2. Click "Admin" in the navigation
3. Approve or reject submitted ideas

## Default Categories

The database initialization creates these categories:
- 🚇 Transportation / Transport
- 🌳 Environment / Environnement
- 🎭 Culture & Events / Culture et événements
- 🏞️ Public Spaces / Espaces publics
- 💻 Technology & Innovation / Technologie et innovation
- 👥 Community & Social / Communauté et social

## Language Switching

Click the language toggle button in the navigation bar to switch between French and English.

## Troubleshooting

**Backend won't start?**
- Make sure the virtual environment is activated
- Check if port 8000 is available

**Frontend won't start?**
- Delete `node_modules` and run `npm install` again
- Make sure port 3000 is available

**Can't connect to backend?**
- Check that backend is running at http://localhost:8000
- Check the `NEXT_PUBLIC_API_URL` in frontend/.env.local

## What's Next?

- Read the full [README.md](README.md) for detailed documentation
- Explore the API docs at http://localhost:8000/docs
- Customize the application to fit your needs

Happy coding! 🚀
