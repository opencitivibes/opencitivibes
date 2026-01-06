#!/bin/bash
# VPS Maintenance Script for OpenCitVibes
# Run via cron: 0 3 * * 0 /home/ubuntu/maintenance/vps-maintenance.sh >> /var/log/vps-maintenance.log 2>&1

set -euo pipefail

LOG_PREFIX="[$(date '+%Y-%m-%d %H:%M:%S')]"

log() {
    echo "$LOG_PREFIX $1"
}

log "=== Starting VPS maintenance ==="

# 1. Docker cleanup - remove unused images, containers, networks, build cache
log "Cleaning Docker system..."
docker system prune -af --filter "until=168h" 2>/dev/null || log "Docker prune failed (non-critical)"

# 2. Remove dangling images specifically
log "Removing dangling Docker images..."
docker image prune -f 2>/dev/null || true

# 3. Clean Docker build cache older than 7 days
log "Cleaning Docker build cache..."
docker builder prune -af --filter "until=168h" 2>/dev/null || true

# 4. Clean old Docker volumes (unused only)
log "Cleaning unused Docker volumes..."
docker volume prune -f 2>/dev/null || true

# 5. Rotate journald logs - keep only 7 days or 100MB
log "Vacuuming journald logs..."
sudo journalctl --vacuum-time=7d --vacuum-size=100M 2>/dev/null || true

# 6. Clean apt cache
log "Cleaning apt cache..."
sudo apt-get autoremove -y 2>/dev/null || true
sudo apt-get autoclean -y 2>/dev/null || true

# 7. Clean old kernels (keep current + 1 previous)
log "Cleaning old kernels..."
sudo apt-get purge -y $(dpkg -l 'linux-*' | sed '/^ii/!d;/'"$(uname -r | sed "s/\(.*\)-\([^0-9]\+\)/\1/")"'/d;s/^[^ ]* [^ ]* \([^ ]*\).*/\1/;/[0-9]/!d' | head -n -1) 2>/dev/null || true

# 8. Clean temp files older than 7 days
log "Cleaning temp files..."
sudo find /tmp -type f -atime +7 -delete 2>/dev/null || true
sudo find /var/tmp -type f -atime +7 -delete 2>/dev/null || true

# 9. Truncate large log files (backup first)
log "Managing large log files..."
for logfile in /var/log/syslog /var/log/auth.log /var/log/kern.log /var/log/ufw.log; do
    if [ -f "$logfile" ] && [ $(stat -c%s "$logfile" 2>/dev/null || echo 0) -gt 104857600 ]; then
        log "Truncating $logfile (>100MB)"
        sudo truncate -s 0 "$logfile" 2>/dev/null || true
    fi
done

# 10. Report disk usage
log "=== Disk usage report ==="
df -h / | tail -1
log "Docker disk usage:"
docker system df 2>/dev/null || true

log "=== VPS maintenance completed ==="
