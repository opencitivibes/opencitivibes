#!/bin/bash
# OpenCitiVibes Backup Script
# Generic backup script for any instance
# Usage: ./scripts/backup.sh [--db-only] [--config-only]

set -euo pipefail

# ============================================
# Configuration (override via environment)
# ============================================
DEPLOY_PATH="${DEPLOY_PATH:-$(pwd)}"
BACKUP_DIR="${BACKUP_DIR:-$DEPLOY_PATH/backups}"
CONTAINER_PREFIX="${CONTAINER_PREFIX:-ocv}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"

# ============================================
# Colors
# ============================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"; }
warn() { echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"; }
error() { echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" >&2; }
info() { echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO:${NC} $1"; }

# ============================================
# Help
# ============================================
show_help() {
    cat << EOF
OpenCitiVibes Backup Script

Usage: ./scripts/backup.sh [OPTIONS]

Options:
    --db-only           Only backup database
    --config-only       Only backup configuration files
    --no-cleanup        Skip cleanup of old backups
    -h, --help          Show this help message

Environment Variables:
    DEPLOY_PATH         Path to deployment directory (default: current dir)
    BACKUP_DIR          Directory for backups (default: ./backups)
    CONTAINER_PREFIX    Docker container prefix (default: ocv)
    RETENTION_DAYS      Days to keep backups (default: 30)

Examples:
    ./scripts/backup.sh                    # Full backup
    ./scripts/backup.sh --db-only          # Database only
    ./scripts/backup.sh --config-only      # Config files only
EOF
    exit 0
}

# ============================================
# Setup
# ============================================
setup() {
    DATE=$(date +%Y%m%d_%H%M%S)
    BACKUP_SUBDIR="$BACKUP_DIR/$DATE"

    mkdir -p "$BACKUP_SUBDIR"
    log "Backup directory: $BACKUP_SUBDIR"
}

# ============================================
# Database Backup
# ============================================
backup_database() {
    log "Backing up database..."
    cd "$DEPLOY_PATH"

    # Load environment
    if [[ -f "$DEPLOY_PATH/.env" ]]; then
        source "$DEPLOY_PATH/.env"
    fi

    local backend_container="${CONTAINER_PREFIX}-backend"

    # Check if backend container is running
    if ! docker ps --format '{{.Names}}' | grep -q "^${backend_container}$"; then
        warn "Backend container not running, trying to find database volume..."

        # Try to backup from volume directly
        local volume_name="${VOLUME_PREFIX:-ocv}-backend-data"
        if docker volume inspect "$volume_name" &>/dev/null; then
            log "Backing up database from volume: $volume_name"
            docker run --rm \
                -v "$volume_name":/data:ro \
                -v "$BACKUP_SUBDIR":/backup \
                alpine sh -c "cp /data/*.db /backup/ 2>/dev/null || echo 'No SQLite files found'"
        else
            warn "No database volume found"
            return 0
        fi
    else
        # Detect database type and backup accordingly
        if docker exec "$backend_container" test -f /app/data/*.db 2>/dev/null; then
            # SQLite backup
            log "Detected SQLite database"

            # Create backup using SQLite's backup command
            docker exec "$backend_container" sh -c \
                "sqlite3 /app/data/*.db '.backup /tmp/backup.db'" 2>/dev/null || true

            # Copy backup file
            docker cp "$backend_container":/tmp/backup.db "$BACKUP_SUBDIR/database.db" 2>/dev/null || {
                # Fallback: direct copy
                docker exec "$backend_container" sh -c \
                    "cp /app/data/*.db /tmp/backup.db" 2>/dev/null || true
                docker cp "$backend_container":/tmp/backup.db "$BACKUP_SUBDIR/database.db" 2>/dev/null || true
            }

            if [[ -f "$BACKUP_SUBDIR/database.db" ]]; then
                gzip "$BACKUP_SUBDIR/database.db"
                log "SQLite backup complete: $BACKUP_SUBDIR/database.db.gz"
            else
                warn "SQLite backup may have failed"
            fi
        else
            # PostgreSQL backup
            log "Detected PostgreSQL database"
            local postgres_container="${CONTAINER_PREFIX}-postgres"

            if docker ps --format '{{.Names}}' | grep -q "^${postgres_container}$"; then
                docker exec "$postgres_container" \
                    pg_dumpall -U "${POSTGRES_USER:-opencitivibes}" | \
                    gzip > "$BACKUP_SUBDIR/database.sql.gz"
                log "PostgreSQL backup complete: $BACKUP_SUBDIR/database.sql.gz"
            else
                warn "PostgreSQL container not running"
            fi
        fi
    fi
}

# ============================================
# Configuration Backup
# ============================================
backup_config() {
    log "Backing up configuration..."
    cd "$DEPLOY_PATH"

    local config_files=()

    # Check for common config files
    [[ -f ".env" ]] && config_files+=(".env")
    [[ -f "docker-compose.yml" ]] && config_files+=("docker-compose.yml")
    [[ -f "backend/config/platform.config.json" ]] && config_files+=("backend/config/platform.config.json")
    [[ -f "backend/config/legal.config.json" ]] && config_files+=("backend/config/legal.config.json")
    [[ -d "nginx/conf.d" ]] && config_files+=("nginx/conf.d")

    if [[ ${#config_files[@]} -eq 0 ]]; then
        warn "No configuration files found"
        return 0
    fi

    tar -czf "$BACKUP_SUBDIR/config.tar.gz" "${config_files[@]}" 2>/dev/null || {
        warn "Some config files could not be backed up"
    }

    log "Configuration backup complete: $BACKUP_SUBDIR/config.tar.gz"
}

# ============================================
# Cleanup Old Backups
# ============================================
cleanup_old_backups() {
    log "Cleaning up backups older than $RETENTION_DAYS days..."

    if [[ -d "$BACKUP_DIR" ]]; then
        # Find and remove old backup directories
        find "$BACKUP_DIR" -maxdepth 1 -type d -mtime +$RETENTION_DAYS -exec rm -rf {} \; 2>/dev/null || true

        # Count remaining backups
        local backup_count=$(find "$BACKUP_DIR" -maxdepth 1 -type d | wc -l)
        info "Remaining backups: $((backup_count - 1))"
    fi
}

# ============================================
# Summary
# ============================================
show_summary() {
    echo ""
    log "Backup Summary:"
    echo ""

    if [[ -d "$BACKUP_SUBDIR" ]]; then
        ls -lh "$BACKUP_SUBDIR"
        echo ""

        local total_size=$(du -sh "$BACKUP_SUBDIR" | cut -f1)
        info "Total backup size: $total_size"
        info "Backup location: $BACKUP_SUBDIR"
    fi

    echo ""
}

# ============================================
# Main
# ============================================
main() {
    local db_only=false
    local config_only=false
    local skip_cleanup=false

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --db-only)
                db_only=true
                shift
                ;;
            --config-only)
                config_only=true
                shift
                ;;
            --no-cleanup)
                skip_cleanup=true
                shift
                ;;
            -h|--help)
                show_help
                ;;
            *)
                error "Unknown option: $1"
                show_help
                ;;
        esac
    done

    echo ""
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  ${NC}${GREEN}OpenCitiVibes Backup${NC}"
    echo -e "${BLUE}║  ${NC}Container prefix: ${YELLOW}$CONTAINER_PREFIX${NC}"
    echo -e "${BLUE}║  ${NC}Retention: ${YELLOW}$RETENTION_DAYS days${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    setup

    if [[ "$config_only" == "true" ]]; then
        backup_config
    elif [[ "$db_only" == "true" ]]; then
        backup_database
    else
        backup_database
        backup_config
    fi

    if [[ "$skip_cleanup" != "true" ]]; then
        cleanup_old_backups
    fi

    show_summary

    log "Backup complete!"
}

main "$@"
