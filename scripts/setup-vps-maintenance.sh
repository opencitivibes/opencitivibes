#!/bin/bash
# Setup script to install maintenance crons on VPS
# Run once: bash setup-vps-maintenance.sh

set -euo pipefail

echo "=== Setting up VPS maintenance ==="

# Create maintenance directory
mkdir -p /home/ubuntu/maintenance
cd /home/ubuntu/maintenance

# Copy scripts (assuming they're in current dir or adjust path)
# If running remotely, scripts should already be copied here

# Make scripts executable
chmod +x /home/ubuntu/maintenance/*.sh 2>/dev/null || true

# Create log file with proper permissions
sudo touch /var/log/vps-maintenance.log
sudo chown ubuntu:ubuntu /var/log/vps-maintenance.log
sudo touch /var/log/disk-alerts.log
sudo chown ubuntu:ubuntu /var/log/disk-alerts.log

# Configure journald to limit disk usage
echo "Configuring journald..."
sudo tee /etc/systemd/journald.conf.d/size-limit.conf > /dev/null << 'EOF'
[Journal]
SystemMaxUse=100M
SystemKeepFree=1G
MaxRetentionSec=7day
EOF

sudo systemctl restart systemd-journald

# Setup crontab for ubuntu user
echo "Installing crontab..."
(crontab -l 2>/dev/null || true; cat << 'EOF'
# VPS Maintenance - Weekly cleanup (Sunday 3 AM)
0 3 * * 0 /home/ubuntu/maintenance/vps-maintenance.sh >> /var/log/vps-maintenance.log 2>&1

# Disk space alert - Every 6 hours
0 */6 * * * /home/ubuntu/maintenance/vps-disk-alert.sh

# Daily Docker image cleanup (keep recent, remove old unused)
0 4 * * * docker image prune -af --filter "until=72h" >> /var/log/vps-maintenance.log 2>&1

# Daily log rotation check
0 5 * * * /usr/sbin/logrotate /etc/logrotate.conf --state /var/lib/logrotate/status
EOF
) | sort -u | crontab -

# Add logrotate config for maintenance logs
sudo tee /etc/logrotate.d/vps-maintenance > /dev/null << 'EOF'
/var/log/vps-maintenance.log /var/log/disk-alerts.log {
    weekly
    rotate 4
    compress
    delaycompress
    missingok
    notifempty
    create 644 ubuntu ubuntu
}
EOF

echo "=== Setup complete ==="
echo ""
echo "Installed cron jobs:"
crontab -l
echo ""
echo "To verify: crontab -l"
echo "To check logs: tail -f /var/log/vps-maintenance.log"
