#!/bin/bash
# OpenCitiVibes Restore Script
# Generic restore script for any instance
# Usage: ./scripts/restore.sh <backup_path> [--db-only] [--config-only]

set -euo pipefail

# ============================================
# Configuration (override via environment)
# ============================================
DEPLOY_PATH="${DEPLOY_PATH:-$(pwd)}"
CONTAINER_PREFIX="${CONTAINER_PREFIX:-ocv}"

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
OpenCitiVibes Restore Script

Usage: ./scripts/restore.sh <backup_path> [OPTIONS]

Arguments:
    backup_path         Path to backup directory (e.g., ./backups/20260106_120000)

Options:
    --db-only           Only restore database
    --config-only       Only restore configuration files
    --no-stop           Don't stop containers before restore (not recommended)
    --dry-run           Show what would be restored without doing it
    -y, --yes           Skip confirmation prompts
    -h, --help          Show this help message

Environment Variables:
    DEPLOY_PATH         Path to deployment directory (default: current dir)
    CONTAINER_PREFIX    Docker container prefix (default: ocv)

Examples:
    ./scripts/restore.sh ./backups/20260106_120000          # Full restore
    ./scripts/restore.sh ./backups/20260106_120000 --db-only # Database only
    ./scripts/restore.sh ./backups/latest --dry-run         # Preview restore

Safety Notes:
    - Containers will be stopped during restore
    - Existing data will be overwritten
    - A pre-restore backup is automatically created
EOF
    exit 0
}

# ============================================
# Validation
# ============================================
validate_backup() {
    local backup_path="$1"

    if [[ ! -d "$backup_path" ]]; then
        error "Backup directory not found: $backup_path"
        exit 1
    fi

    # Check for at least one backup file
    if [[ ! -f "$backup_path/database.db.gz" ]] && \
       [[ ! -f "$backup_path/database.sql.gz" ]] && \
       [[ ! -f "$backup_path/config.tar.gz" ]]; then
        error "No valid backup files found in: $backup_path"
        echo ""
        echo "Expected files:"
        echo "  - database.db.gz (SQLite backup)"
        echo "  - database.sql.gz (PostgreSQL backup)"
        echo "  - config.tar.gz (configuration backup)"
        exit 1
    fi

    log "Backup validated: $backup_path"
    ls -lh "$backup_path"
    echo ""
}

# ============================================
# Pre-restore Backup
# ============================================
create_pre_restore_backup() {
    log "Creating pre-restore backup..."

    local pre_restore_dir="$DEPLOY_PATH/backups/pre-restore-$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$pre_restore_dir"

    # Quick backup of current database
    local backend_container="${CONTAINER_PREFIX}-backend"

    if docker ps --format '{{.Names}}' | grep -q "^${backend_container}$"; then
        # SQLite
        if docker exec "$backend_container" test -f /app/data/*.db 2>/dev/null; then
            docker exec "$backend_container" sh -c \
                "cp /app/data/*.db /tmp/pre-restore.db" 2>/dev/null || true
            docker cp "$backend_container":/tmp/pre-restore.db "$pre_restore_dir/database.db" 2>/dev/null || true
        fi
    fi

    # Backup current config
    if [[ -f "$DEPLOY_PATH/.env" ]]; then
        cp "$DEPLOY_PATH/.env" "$pre_restore_dir/"
    fi

    info "Pre-restore backup saved to: $pre_restore_dir"
}

# ============================================
# Stop Containers
# ============================================
stop_containers() {
    log "Stopping containers..."
    cd "$DEPLOY_PATH"

    # Try different profiles
    docker compose --profile staging down 2>/dev/null || \
    docker compose --profile prod down 2>/dev/null || \
    docker compose down 2>/dev/null || true

    # Wait for containers to stop
    sleep 3

    info "Containers stopped"
}

# ============================================
# Start Containers
# ============================================
start_containers() {
    log "Starting containers..."
    cd "$DEPLOY_PATH"

    # Detect which profile to use based on .env
    local profile="staging"
    if grep -q "ENVIRONMENT=production" "$DEPLOY_PATH/.env" 2>/dev/null; then
        profile="prod"
    fi

    docker compose --profile "$profile" up -d

    # Wait for containers to be healthy
    log "Waiting for containers to be healthy..."
    sleep 10

    info "Containers started with profile: $profile"
}

# ============================================
# Restore Database
# ============================================
restore_database() {
    local backup_path="$1"
    local dry_run="$2"

    log "Restoring database..."
    cd "$DEPLOY_PATH"

    # Load environment
    if [[ -f "$DEPLOY_PATH/.env" ]]; then
        source "$DEPLOY_PATH/.env"
    fi

    local backend_container="${CONTAINER_PREFIX}-backend"

    # Check for SQLite backup
    if [[ -f "$backup_path/database.db.gz" ]]; then
        log "Found SQLite backup"

        if [[ "$dry_run" == "true" ]]; then
            info "[DRY RUN] Would restore SQLite database from: $backup_path/database.db.gz"
            return 0
        fi

        # Decompress backup
        local temp_db="/tmp/restore_db_$$.db"
        gunzip -c "$backup_path/database.db.gz" > "$temp_db"

        # Get the database filename from the container
        local db_name=$(docker exec "$backend_container" sh -c "ls /app/data/*.db 2>/dev/null | head -1 | xargs basename" 2>/dev/null || echo "database.db")

        # Copy to container
        docker cp "$temp_db" "$backend_container:/app/data/$db_name"

        # Fix permissions
        docker exec "$backend_container" chown -R 1000:1000 /app/data/ 2>/dev/null || true

        # Cleanup
        rm -f "$temp_db"

        log "SQLite database restored successfully"

    # Check for PostgreSQL backup
    elif [[ -f "$backup_path/database.sql.gz" ]]; then
        log "Found PostgreSQL backup"

        if [[ "$dry_run" == "true" ]]; then
            info "[DRY RUN] Would restore PostgreSQL database from: $backup_path/database.sql.gz"
            return 0
        fi

        local postgres_container="${CONTAINER_PREFIX}-postgres"

        if ! docker ps --format '{{.Names}}' | grep -q "^${postgres_container}$"; then
            error "PostgreSQL container not running: $postgres_container"
            return 1
        fi

        # Decompress and restore
        gunzip -c "$backup_path/database.sql.gz" | \
            docker exec -i "$postgres_container" psql -U "${POSTGRES_USER:-opencitivibes}"

        log "PostgreSQL database restored successfully"

    else
        warn "No database backup found in: $backup_path"
    fi
}

# ============================================
# Restore Configuration
# ============================================
restore_config() {
    local backup_path="$1"
    local dry_run="$2"

    log "Restoring configuration..."
    cd "$DEPLOY_PATH"

    if [[ ! -f "$backup_path/config.tar.gz" ]]; then
        warn "No configuration backup found in: $backup_path"
        return 0
    fi

    if [[ "$dry_run" == "true" ]]; then
        info "[DRY RUN] Would restore configuration from: $backup_path/config.tar.gz"
        echo "Contents:"
        tar -tzf "$backup_path/config.tar.gz" | head -20
        return 0
    fi

    # Extract config files
    tar -xzf "$backup_path/config.tar.gz" -C "$DEPLOY_PATH"

    log "Configuration restored successfully"
}

# ============================================
# Main
# ============================================
main() {
    local backup_path=""
    local db_only=false
    local config_only=false
    local no_stop=false
    local dry_run=false
    local skip_confirm=false

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
            --no-stop)
                no_stop=true
                shift
                ;;
            --dry-run)
                dry_run=true
                shift
                ;;
            -y|--yes)
                skip_confirm=true
                shift
                ;;
            -h|--help)
                show_help
                ;;
            -*)
                error "Unknown option: $1"
                show_help
                ;;
            *)
                if [[ -z "$backup_path" ]]; then
                    backup_path="$1"
                else
                    error "Unexpected argument: $1"
                    show_help
                fi
                shift
                ;;
        esac
    done

    # Check for backup path
    if [[ -z "$backup_path" ]]; then
        error "Backup path required"
        echo ""
        show_help
    fi

    # Handle "latest" shortcut
    if [[ "$backup_path" == "latest" ]] || [[ "$backup_path" == "./backups/latest" ]]; then
        backup_path=$(ls -td "$DEPLOY_PATH/backups"/*/ 2>/dev/null | head -1)
        if [[ -z "$backup_path" ]]; then
            error "No backups found in $DEPLOY_PATH/backups/"
            exit 1
        fi
        info "Using latest backup: $backup_path"
    fi

    echo ""
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  ${NC}${GREEN}OpenCitiVibes Restore${NC}"
    echo -e "${BLUE}║  ${NC}Container prefix: ${YELLOW}$CONTAINER_PREFIX${NC}"
    echo -e "${BLUE}║  ${NC}Backup: ${YELLOW}$backup_path${NC}"
    if [[ "$dry_run" == "true" ]]; then
        echo -e "${BLUE}║  ${NC}Mode: ${YELLOW}DRY RUN${NC}"
    fi
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    # Validate backup
    validate_backup "$backup_path"

    # Confirmation
    if [[ "$skip_confirm" != "true" ]] && [[ "$dry_run" != "true" ]]; then
        echo -e "${RED}WARNING: This will overwrite existing data!${NC}"
        echo ""
        read -p "Are you sure you want to restore? (yes/no): " confirm
        if [[ "$confirm" != "yes" ]]; then
            log "Restore cancelled"
            exit 0
        fi
        echo ""
    fi

    # Create pre-restore backup (unless dry run)
    if [[ "$dry_run" != "true" ]]; then
        create_pre_restore_backup
    fi

    # Stop containers (unless --no-stop or dry run)
    if [[ "$no_stop" != "true" ]] && [[ "$dry_run" != "true" ]]; then
        stop_containers
    fi

    # Perform restore
    if [[ "$config_only" == "true" ]]; then
        restore_config "$backup_path" "$dry_run"
    elif [[ "$db_only" == "true" ]]; then
        restore_database "$backup_path" "$dry_run"
    else
        restore_database "$backup_path" "$dry_run"
        restore_config "$backup_path" "$dry_run"
    fi

    # Start containers (unless --no-stop or dry run)
    if [[ "$no_stop" != "true" ]] && [[ "$dry_run" != "true" ]]; then
        start_containers
    fi

    echo ""
    if [[ "$dry_run" == "true" ]]; then
        log "Dry run complete - no changes made"
    else
        log "Restore complete!"
        echo ""
        info "Run 'docker compose logs -f' to verify services are healthy"
    fi
}

main "$@"
