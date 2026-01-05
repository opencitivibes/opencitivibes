#!/bin/sh
# docker-entrypoint.dev.sh
# Fixes permissions on volumes and runs command as specified user

# Get target user from environment (set by docker-compose user directive)
TARGET_UID="${DOCKER_UID:-1000}"
TARGET_GID="${DOCKER_GID:-1000}"

# Fix ownership of node_modules (anonymous volume created as root)
if [ -d /app/node_modules ]; then
    chown -R "$TARGET_UID:$TARGET_GID" /app/node_modules 2>/dev/null || true
fi

# Ensure .next directory exists with correct permissions
mkdir -p /app/.next
chown -R "$TARGET_UID:$TARGET_GID" /app/.next 2>/dev/null || true

# Run command as the target user using su-exec (Alpine's lightweight sudo)
exec su-exec "$TARGET_UID:$TARGET_GID" "$@"
