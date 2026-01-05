#!/bin/bash
# Setup ntfy authentication and access control
# Run this once after ntfy container starts
#
# Usage: ./scripts/setup-ntfy-auth.sh
#
# This script will:
# 1. Create a backend service account for publishing notifications
# 2. Generate an auth token for the backend
# 3. Display instructions for adding admin users

set -e

# Load environment variables if .env exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

CONTAINER_NAME="${CONTAINER_PREFIX:-ocv}-ntfy"
TOPIC_PREFIX="${NTFY_TOPIC_PREFIX:-admin}"

echo "=== Setting up ntfy authentication ==="
echo "Container: $CONTAINER_NAME"
echo "Topic prefix: $TOPIC_PREFIX"
echo ""

# Check if container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "Error: Container $CONTAINER_NAME is not running"
    echo "Start it with: docker compose up -d ntfy"
    exit 1
fi

# Check if backend-publisher user already exists
if docker exec "$CONTAINER_NAME" ntfy user list 2>/dev/null | grep -q "backend-publisher"; then
    echo "Backend-publisher user already exists"
    echo ""
    echo "To regenerate token, run:"
    echo "  docker exec $CONTAINER_NAME ntfy token add --label=backend-publisher --expires=never backend-publisher"
    echo ""
else
    # 1. Create backend service account (for publishing)
    echo "Creating backend service account..."
    echo "You will be prompted to enter a password for the backend-publisher account."
    echo "(This password is just for account creation - we'll use a token for auth)"
    echo ""

    docker exec -it "$CONTAINER_NAME" ntfy user add \
        --role=admin \
        backend-publisher

    echo ""
    echo "Backend-publisher user created successfully!"
fi

# 2. Grant publish access to admin topics
echo ""
echo "Setting up topic access control..."
docker exec "$CONTAINER_NAME" ntfy access backend-publisher "${TOPIC_PREFIX}-*" write 2>/dev/null || true
echo "Granted write access to ${TOPIC_PREFIX}-* topics"

# 3. Generate auth token
echo ""
echo "=== Generating auth token ==="
echo "The following token should be added to your .env file as NTFY_AUTH_TOKEN"
echo ""

TOKEN=$(docker exec "$CONTAINER_NAME" ntfy token add \
    --label="backend-publisher" \
    --expires=never \
    backend-publisher 2>/dev/null || echo "")

if [ -n "$TOKEN" ]; then
    echo "Token: $TOKEN"
    echo ""
    echo "Add to your .env file:"
    echo "  NTFY_AUTH_TOKEN=$TOKEN"
else
    echo "Token generation failed or token already exists."
    echo "List existing tokens with:"
    echo "  docker exec $CONTAINER_NAME ntfy token list backend-publisher"
fi

echo ""
echo "=== Setup complete ==="
echo ""
echo "Next steps:"
echo ""
echo "1. Add the token to your backend .env file:"
echo "   NTFY_AUTH_TOKEN=<token-from-above>"
echo ""
echo "2. Create admin user accounts for each person who needs notifications:"
echo "   docker exec -it $CONTAINER_NAME ntfy user add <username>"
echo ""
echo "3. Grant read access to each admin user:"
echo "   docker exec $CONTAINER_NAME ntfy access <username> ${TOPIC_PREFIX}-* read"
echo ""
echo "4. Share the ntfy server URL with admins:"
echo "   - Server: https://ntfy.yourdomain.com"
echo "   - Topics to subscribe: ${TOPIC_PREFIX}-ideas, ${TOPIC_PREFIX}-comments, etc."
echo ""
echo "See docs/ADMIN_NOTIFICATIONS.md for admin onboarding guide."
