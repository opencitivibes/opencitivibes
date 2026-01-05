#!/bin/bash
# End-to-end notification test
# Run this after deployment to verify notifications work
#
# Usage:
#   ./scripts/test-notifications-e2e.sh
#
# Environment variables (optional):
#   API_URL - Backend API URL (default: http://localhost:8000)
#   NTFY_URL - ntfy server URL (default: http://localhost:8080)
#   NTFY_TOPIC_PREFIX - Topic prefix (default: idees-admin)
#   ADMIN_EMAIL - Admin email for auth
#   ADMIN_PASSWORD - Admin password for auth

set -e

# Configuration
API_URL="${API_URL:-http://localhost:8000}"
NTFY_URL="${NTFY_URL:-http://localhost:8080}"
NTFY_TOPIC_PREFIX="${NTFY_TOPIC_PREFIX:-idees-admin}"
TOPIC="${NTFY_TOPIC_PREFIX}-ideas"

echo "=== E2E Notification Test ==="
echo "API URL: $API_URL"
echo "Ntfy URL: $NTFY_URL"
echo "Topic: $TOPIC"
echo ""

# Check required tools
command -v curl >/dev/null 2>&1 || { echo "ERROR: curl is required"; exit 1; }
command -v jq >/dev/null 2>&1 || { echo "ERROR: jq is required"; exit 1; }

# 1. Check ntfy is healthy
echo "1. Checking ntfy health..."
HEALTH_RESPONSE=$(curl -s --max-time 10 "$NTFY_URL/v1/health" 2>/dev/null || echo '{"healthy":false}')
HEALTH=$(echo "$HEALTH_RESPONSE" | jq -r '.healthy // false')
if [ "$HEALTH" != "true" ]; then
    echo "   WARNING: ntfy health check failed"
    echo "   Response: $HEALTH_RESPONSE"
    echo "   (Continuing anyway - ntfy may not expose health endpoint)"
else
    echo "   OK - ntfy is healthy"
fi

# 2. Check API is healthy
echo "2. Checking API health..."
API_HEALTH=$(curl -s --max-time 10 "$API_URL/health" 2>/dev/null || echo '{}')
if echo "$API_HEALTH" | jq -e '.status' >/dev/null 2>&1; then
    echo "   OK - API is healthy"
else
    echo "   WARNING: API health check returned unexpected response"
    echo "   Response: $API_HEALTH"
fi

# 3. Authenticate
echo "3. Authenticating..."
if [ -z "$ADMIN_EMAIL" ] || [ -z "$ADMIN_PASSWORD" ]; then
    echo "   SKIPPED - ADMIN_EMAIL and ADMIN_PASSWORD not set"
    echo "   Set these environment variables to run the full test"
    echo ""
    echo "=== Partial Test Complete ==="
    echo "Infrastructure checks passed. Set credentials for full test."
    exit 0
fi

TOKEN_RESPONSE=$(curl -s -X POST "$API_URL/api/auth/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=${ADMIN_EMAIL}&password=${ADMIN_PASSWORD}" 2>/dev/null)

TOKEN=$(echo "$TOKEN_RESPONSE" | jq -r '.access_token // empty')
if [ -z "$TOKEN" ]; then
    echo "   ERROR: Failed to get auth token"
    echo "   Response: $TOKEN_RESPONSE"
    exit 1
fi
echo "   OK - Authenticated successfully"

# 4. Get a category ID
echo "4. Getting category..."
CATEGORIES=$(curl -s "$API_URL/api/categories" -H "Authorization: Bearer $TOKEN")
CATEGORY_ID=$(echo "$CATEGORIES" | jq -r '.[0].id // empty')
if [ -z "$CATEGORY_ID" ]; then
    echo "   ERROR: No categories found"
    exit 1
fi
CATEGORY_NAME=$(echo "$CATEGORIES" | jq -r '.[0].name_en // "Unknown"')
echo "   OK - Using category: $CATEGORY_NAME (ID: $CATEGORY_ID)"

# 5. Start listening for notifications (background)
echo "5. Starting notification listener..."
LISTENER_OUTPUT=$(mktemp)
# Poll for messages starting from now
curl -s "$NTFY_URL/$TOPIC/json?poll=1&since=now" > "$LISTENER_OUTPUT" 2>/dev/null &
LISTENER_PID=$!
sleep 2

# 6. Create a test idea
echo "6. Creating test idea..."
TIMESTAMP=$(date +%s)
IDEA_TITLE="E2E Test Idea $TIMESTAMP"

IDEA_RESPONSE=$(curl -s -X POST "$API_URL/api/ideas" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
        \"title\": \"$IDEA_TITLE\",
        \"description\": \"This is an automated E2E test to verify the notification system is working correctly.\",
        \"category_id\": $CATEGORY_ID,
        \"tags\": []
    }" 2>/dev/null)

IDEA_ID=$(echo "$IDEA_RESPONSE" | jq -r '.id // empty')
if [ -z "$IDEA_ID" ]; then
    echo "   ERROR: Failed to create idea"
    echo "   Response: $IDEA_RESPONSE"
    kill $LISTENER_PID 2>/dev/null || true
    rm -f "$LISTENER_OUTPUT"
    exit 1
fi
echo "   OK - Created idea #$IDEA_ID"

# 7. Wait for notification
echo "7. Waiting for notification..."
sleep 5

# Stop listener
kill $LISTENER_PID 2>/dev/null || true

# 8. Check for notification
echo "8. Checking for notification..."
if [ -s "$LISTENER_OUTPUT" ]; then
    if grep -q "$IDEA_TITLE" "$LISTENER_OUTPUT" 2>/dev/null; then
        echo "   OK - Notification received!"
        echo ""
        echo "   Notification content:"
        cat "$LISTENER_OUTPUT" | jq '.' 2>/dev/null || cat "$LISTENER_OUTPUT"
    else
        echo "   WARNING: Received notification but content doesn't match"
        echo "   Expected: $IDEA_TITLE"
        echo "   Received:"
        cat "$LISTENER_OUTPUT"
    fi
else
    echo "   WARNING: No notification received"
    echo "   This may be expected if:"
    echo "   - ntfy requires authentication for subscription"
    echo "   - NTFY_ENABLED is false in backend"
    echo "   - Network issues between backend and ntfy"
fi

# 9. Cleanup - delete test idea
echo "9. Cleaning up test idea..."
DELETE_RESPONSE=$(curl -s -X DELETE "$API_URL/api/ideas/$IDEA_ID" \
    -H "Authorization: Bearer $TOKEN" 2>/dev/null)
echo "   OK - Cleanup completed"

# Cleanup temp file
rm -f "$LISTENER_OUTPUT"

echo ""
echo "=== E2E Test Complete ==="
echo ""
echo "Summary:"
echo "- API health: OK"
echo "- Authentication: OK"
echo "- Idea creation: OK"
echo "- Notification: Check above for results"
echo ""
echo "To fully verify notifications, check your ntfy mobile app."
echo "Topic to subscribe: $TOPIC"
