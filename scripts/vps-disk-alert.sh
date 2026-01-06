#!/bin/bash
# Disk space alert script - sends notification when disk is >80% full
# Run via cron: 0 */6 * * * /home/ubuntu/maintenance/vps-disk-alert.sh

THRESHOLD=80
NTFY_TOPIC="dev-admin-ideas"  # Your ntfy topic
NTFY_URL="http://localhost:8080"  # Local ntfy container

USAGE=$(df / | tail -1 | awk '{print $5}' | tr -d '%')

if [ "$USAGE" -gt "$THRESHOLD" ]; then
    MESSAGE="ALERT: Disk usage at ${USAGE}% on $(hostname)"

    # Send to ntfy
    curl -s -X POST "$NTFY_URL/$NTFY_TOPIC" \
        -H "Title: Disk Space Warning" \
        -H "Priority: high" \
        -H "Tags: warning,disk" \
        -d "$MESSAGE" 2>/dev/null || true

    # Also log it
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $MESSAGE" >> /var/log/disk-alerts.log
fi
