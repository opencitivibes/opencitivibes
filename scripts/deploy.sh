#!/bin/bash
# OpenCitiVibes Deployment Script
# Generic deployment script for any instance
# Usage: ./scripts/deploy.sh [--rollback]

set -euo pipefail

# ============================================
# Configuration (override via environment)
# ============================================
DEPLOY_PATH="${DEPLOY_PATH:-$(pwd)}"
COMPOSE_PROJECT="${COMPOSE_PROJECT_NAME:-opencitivibes}"
COMPOSE_PROFILE="${COMPOSE_PROFILE:-prod}"
BACKUP_BEFORE_DEPLOY="${BACKUP_BEFORE_DEPLOY:-true}"
HEALTH_CHECK_TIMEOUT="${HEALTH_CHECK_TIMEOUT:-60}"

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
OpenCitiVibes Deployment Script

Usage: ./scripts/deploy.sh [OPTIONS]

Options:
    --profile PROFILE   Docker Compose profile (dev, staging, prod) [default: prod]
    --rollback          Rollback to previous deployment
    --no-backup         Skip pre-deployment backup
    --force             Force deployment without health checks
    -h, --help          Show this help message

Environment Variables:
    DEPLOY_PATH         Path to deployment directory (default: current dir)
    COMPOSE_PROJECT_NAME    Docker Compose project name
    COMPOSE_PROFILE     Docker Compose profile (default: prod)
    HEALTH_CHECK_TIMEOUT    Timeout for health checks in seconds (default: 60)

Examples:
    ./scripts/deploy.sh                    # Production deployment
    ./scripts/deploy.sh --profile staging  # Staging deployment
    ./scripts/deploy.sh --no-backup        # Deploy without backup
    ./scripts/deploy.sh --rollback         # Rollback to previous version
EOF
    exit 0
}

# ============================================
# Requirements Check
# ============================================
check_requirements() {
    log "Checking requirements..."

    # Check .env file
    if [[ ! -f "$DEPLOY_PATH/.env" ]]; then
        error ".env file not found at $DEPLOY_PATH/.env"
        exit 1
    fi

    # Check docker-compose.yml
    if [[ ! -f "$DEPLOY_PATH/docker-compose.yml" ]]; then
        error "docker-compose.yml not found at $DEPLOY_PATH"
        exit 1
    fi

    # Check Docker
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed"
        exit 1
    fi

    # Check Docker Compose
    if ! docker compose version &> /dev/null; then
        error "Docker Compose is not available"
        exit 1
    fi

    # Check platform config
    if [[ ! -f "$DEPLOY_PATH/backend/config/platform.config.json" ]]; then
        warn "platform.config.json not found - using defaults"
    fi

    # Check legal documents
    if [[ ! -d "$DEPLOY_PATH/backend/config/legal" ]]; then
        warn "Legal documents directory not found at backend/config/legal/"
        warn "Terms and Privacy pages will show 'content not available'"
        warn "Upload from instances/{name}/legal/ before deployment"
    fi

    log "Requirements check passed"
}

# ============================================
# Backup
# ============================================
create_backup() {
    if [[ "$BACKUP_BEFORE_DEPLOY" != "true" ]]; then
        info "Skipping backup (BACKUP_BEFORE_DEPLOY=false)"
        return
    fi

    if [[ -f "$DEPLOY_PATH/scripts/backup.sh" ]]; then
        log "Creating pre-deployment backup..."
        bash "$DEPLOY_PATH/scripts/backup.sh" || warn "Backup failed, continuing deployment"
    else
        warn "Backup script not found, skipping backup"
    fi
}

# ============================================
# Pull Images
# ============================================
pull_images() {
    log "Pulling latest images..."
    cd "$DEPLOY_PATH"
    docker compose --profile "$COMPOSE_PROFILE" pull
}

# ============================================
# Store Current State (for rollback)
# ============================================
store_current_state() {
    log "Storing current deployment state..."
    cd "$DEPLOY_PATH"

    # Store current image digests
    docker compose --profile "$COMPOSE_PROFILE" images --format json 2>/dev/null > /tmp/deployment_state_previous.json || true
}

# ============================================
# Deploy
# ============================================
deploy() {
    log "Deploying..."
    cd "$DEPLOY_PATH"

    # Generate nginx config from templates if needed
    if [[ -f "$DEPLOY_PATH/nginx/conf.d/default.conf.template" ]]; then
        info "Generating nginx configuration from templates..."
        source "$DEPLOY_PATH/.env"
        envsubst '${DOMAIN} ${CONTAINER_PREFIX}' \
            < "$DEPLOY_PATH/nginx/conf.d/default.conf.template" \
            > "$DEPLOY_PATH/nginx/conf.d/default.conf"
    fi

    # Generate ntfy nginx config from template
    if [[ -f "$DEPLOY_PATH/nginx/conf.d/ntfy.conf.template" ]]; then
        info "Generating ntfy nginx configuration from template..."
        source "$DEPLOY_PATH/.env"
        envsubst '${DOMAIN} ${CONTAINER_PREFIX}' \
            < "$DEPLOY_PATH/nginx/conf.d/ntfy.conf.template" \
            > "$DEPLOY_PATH/nginx/conf.d/ntfy.conf"
    fi

    # Rolling update
    docker compose --profile "$COMPOSE_PROFILE" up -d --remove-orphans

    log "Containers started, waiting for health checks..."
}

# ============================================
# Health Check
# ============================================
wait_for_health() {
    local timeout=$HEALTH_CHECK_TIMEOUT
    local elapsed=0
    local interval=5

    log "Waiting for services to be healthy (timeout: ${timeout}s)..."

    while [[ $elapsed -lt $timeout ]]; do
        sleep $interval
        elapsed=$((elapsed + interval))

        # Check if any containers are unhealthy
        if docker compose --profile "$COMPOSE_PROFILE" ps 2>/dev/null | grep -q "unhealthy"; then
            info "Services still starting... (${elapsed}s/${timeout}s)"
            continue
        fi

        # Check if all containers are running
        local running_count=$(docker compose --profile "$COMPOSE_PROFILE" ps --status running -q 2>/dev/null | wc -l)
        local total_count=$(docker compose --profile "$COMPOSE_PROFILE" ps -q 2>/dev/null | wc -l)

        if [[ $running_count -eq $total_count ]] && [[ $total_count -gt 0 ]]; then
            log "All services healthy!"
            return 0
        fi

        info "Waiting for services... (${elapsed}s/${timeout}s)"
    done

    return 1
}

# ============================================
# Verify Deployment
# ============================================
verify_deployment() {
    log "Verifying deployment..."
    cd "$DEPLOY_PATH"

    # Check container status
    if docker compose --profile "$COMPOSE_PROFILE" ps 2>/dev/null | grep -q "unhealthy"; then
        error "Deployment verification failed - unhealthy containers detected"
        docker compose --profile "$COMPOSE_PROFILE" ps
        return 1
    fi

    # Check if containers are running
    if docker compose --profile "$COMPOSE_PROFILE" ps --status running -q 2>/dev/null | wc -l | grep -q "^0$"; then
        error "Deployment verification failed - no running containers"
        return 1
    fi

    log "Deployment verified successfully!"
    docker compose --profile "$COMPOSE_PROFILE" ps
    return 0
}

# ============================================
# Cleanup
# ============================================
cleanup() {
    log "Cleaning up old resources..."
    docker system prune -f --volumes 2>/dev/null || true
    docker image prune -f 2>/dev/null || true
}

# ============================================
# Rollback
# ============================================
rollback() {
    log "Rolling back to previous deployment..."
    cd "$DEPLOY_PATH"

    if [[ ! -f /tmp/deployment_state_previous.json ]]; then
        error "No previous deployment state found"
        exit 1
    fi

    warn "Rollback is a manual process. Previous images:"
    cat /tmp/deployment_state_previous.json

    info "To rollback manually:"
    info "1. Edit .env and set IMAGE_TAG to previous version"
    info "2. Run: docker compose --profile $COMPOSE_PROFILE pull && docker compose --profile $COMPOSE_PROFILE up -d"
    exit 1
}

# ============================================
# Main
# ============================================
main() {
    local do_rollback=false
    local force=false

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --profile)
                if [[ -n "${2:-}" ]] && [[ "$2" =~ ^(dev|staging|prod)$ ]]; then
                    COMPOSE_PROFILE="$2"
                    shift 2
                else
                    error "Invalid or missing profile. Use: dev, staging, or prod"
                    exit 1
                fi
                ;;
            --rollback)
                do_rollback=true
                shift
                ;;
            --no-backup)
                BACKUP_BEFORE_DEPLOY=false
                shift
                ;;
            --force)
                force=true
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
    echo -e "${BLUE}║  ${NC}${GREEN}OpenCitiVibes Deployment${NC}"
    echo -e "${BLUE}║  ${NC}Project: ${YELLOW}$COMPOSE_PROJECT${NC}"
    echo -e "${BLUE}║  ${NC}Profile: ${YELLOW}$COMPOSE_PROFILE${NC}"
    echo -e "${BLUE}║  ${NC}Path: ${YELLOW}$DEPLOY_PATH${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    if [[ "$do_rollback" == "true" ]]; then
        rollback
        exit 0
    fi

    check_requirements
    create_backup
    store_current_state
    pull_images
    deploy

    if [[ "$force" != "true" ]]; then
        if ! wait_for_health; then
            error "Health check timeout - deployment may have failed"
            docker compose --profile "$COMPOSE_PROFILE" ps
            exit 1
        fi

        if ! verify_deployment; then
            error "Deployment verification failed"
            exit 1
        fi
    else
        warn "Skipping health checks (--force)"
    fi

    cleanup

    echo ""
    log "Deployment complete!"
    echo ""
}

main "$@"
