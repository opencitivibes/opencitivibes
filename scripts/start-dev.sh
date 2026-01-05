#!/bin/bash
# Start both frontend and backend dev servers
# Usage: ./scripts/start-dev.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Check if instance is configured
if [ ! -f "$PROJECT_ROOT/backend/.env.instance" ]; then
  echo "No instance configured. Run:"
  echo "  ./scripts/switch-instance.sh <instance>"
  echo ""
  "$SCRIPT_DIR/switch-instance.sh" status
  exit 1
fi

# Fix any permission issues from Docker (if .next exists and is not writable)
if [ -d "$PROJECT_ROOT/frontend/.next" ] && [ ! -w "$PROJECT_ROOT/frontend/.next" ]; then
  echo "Fixing .next directory permissions..."
  sudo chown -R "$(id -u):$(id -g)" "$PROJECT_ROOT/frontend/.next"
fi

# Show current instance
echo "=== Starting Dev Servers ==="
if [ -f "$PROJECT_ROOT/.active-instance" ]; then
  echo "Instance: $(cat "$PROJECT_ROOT/.active-instance")"
fi
echo ""

# Kill any existing servers
pkill -f "uvicorn main:app" 2>/dev/null || true
pkill -f "next dev" 2>/dev/null || true
sleep 1

# Start backend
echo "[Backend] Starting on port 8000..."
cd "$PROJECT_ROOT/backend"

# Save any environment overrides before sourcing
_OVERRIDE_DATABASE_URL="${DATABASE_URL:-}"
_OVERRIDE_PLATFORM_CONFIG_PATH="${PLATFORM_CONFIG_PATH:-}"

source .env.instance

# Restore overrides if they were set (allows: DATABASE_URL=... ./start-dev.sh)
[ -n "$_OVERRIDE_DATABASE_URL" ] && export DATABASE_URL="$_OVERRIDE_DATABASE_URL"
[ -n "$_OVERRIDE_PLATFORM_CONFIG_PATH" ] && export PLATFORM_CONFIG_PATH="$_OVERRIDE_PLATFORM_CONFIG_PATH"

echo "  Database: $DATABASE_URL"
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Wait for backend
sleep 3

# Start frontend
echo "[Frontend] Starting on port 3000..."
cd "$PROJECT_ROOT/frontend"
pnpm dev --port 3000 &
FRONTEND_PID=$!

echo ""
echo "=== Servers Started ==="
echo "  Frontend: http://localhost:3000"
echo "  Backend:  http://localhost:8000"
echo "  API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop both servers"

# Wait for either to exit
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
