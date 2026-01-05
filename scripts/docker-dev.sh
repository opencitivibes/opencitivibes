#!/bin/bash
# scripts/docker-dev.sh
# OpenCitiVibes Docker Development Tool
# Docker development commands with optional remote VM support

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Remote execution variables
REMOTE_HOST=""
REMOTE_PATH=""
REMOTE_SYNC=false
REMOTE_SSH_OPTS=""
DRY_RUN=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Compose file for development
COMPOSE_FILE="docker-compose.dev.yml"

# Instance selection
INSTANCES_DIR="$PROJECT_ROOT/instances"
SELECTED_INSTANCE=""

# Get list of available instances
get_instances() {
    for dir in "$INSTANCES_DIR"/*/; do
        [ -d "$dir" ] && [ -f "$dir/platform.config.json" ] && basename "$dir"
    done
}

# Show available instances
show_instances() {
    echo -e "${CYAN}Available instances:${NC}"
    local current=$(cat "$PROJECT_ROOT/.active-instance" 2>/dev/null || echo "none")
    for instance in $(get_instances); do
        if [ "$instance" = "$current" ]; then
            echo -e "  ${GREEN}● $instance${NC} (active)"
        else
            echo -e "  ○ $instance"
        fi
    done
}

# Switch to specified instance
switch_instance() {
    local instance="$1"

    if [ ! -f "$INSTANCES_DIR/$instance/platform.config.json" ]; then
        echo -e "${RED}Error: Instance '$instance' not found${NC}"
        echo ""
        show_instances
        exit 1
    fi

    echo -e "${MAGENTA}Switching to $instance instance...${NC}"

    # Call the switch-instance script
    if [ -f "$SCRIPT_DIR/switch-instance.sh" ]; then
        "$SCRIPT_DIR/switch-instance.sh" "$instance"
    else
        echo -e "${RED}Error: switch-instance.sh not found${NC}"
        exit 1
    fi
}

# Load environment for container prefix
load_env() {
    if [ -f "$PROJECT_ROOT/.env" ]; then
        export $(grep -v '^#' "$PROJECT_ROOT/.env" | xargs) 2>/dev/null || true
    fi
    CONTAINER_PREFIX="${CONTAINER_PREFIX:-ocv}"
    # Export UID/GID for running containers as current user (avoids root-owned files)
    # Note: UID is readonly in bash, so we use DOCKER_UID/DOCKER_GID
    export DOCKER_UID=$(id -u)
    export DOCKER_GID=$(id -g)
}

# Load remote config if exists
load_remote_config() {
    local config_file="$PROJECT_ROOT/.docker-remote.env"
    if [ -f "$config_file" ]; then
        # Source with error handling
        set -a
        # shellcheck source=/dev/null
        source "$config_file" 2>/dev/null || true
        set +a
        REMOTE_HOST="${DOCKER_REMOTE_HOST:-}"
        REMOTE_PATH="${DOCKER_REMOTE_PATH:-/home/$USER/opencitivibes}"
        REMOTE_SYNC="${DOCKER_REMOTE_SYNC:-false}"
        REMOTE_SSH_OPTS="${DOCKER_REMOTE_SSH_OPTS:-}"
    fi
}

# Parse command line arguments
parse_args() {
    local args=()
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --remote)
                shift
                # Check if next arg is a host (contains @) or another flag/command
                if [[ $# -gt 0 && "$1" =~ @ && ! "$1" =~ ^-- ]]; then
                    # Load config for other settings (path, ssh opts)
                    load_remote_config
                    # Override host with CLI value
                    REMOTE_HOST="$1"
                    # Set default path if not set by config
                    if [ -z "$REMOTE_PATH" ]; then
                        local remote_user="${REMOTE_HOST%%@*}"
                        REMOTE_PATH="/home/${remote_user}/opencitivibes"
                    fi
                    shift
                else
                    # Use config file host
                    load_remote_config
                    if [ -z "$REMOTE_HOST" ]; then
                        echo -e "${RED}Error: --remote requires user@host or .docker-remote.env config${NC}"
                        echo ""
                        echo "Options:"
                        echo "  1. Provide host: --remote user@192.168.1.100"
                        echo "  2. Create config: cp .docker-remote.env.example .docker-remote.env"
                        exit 1
                    fi
                fi
                ;;
            --sync)
                REMOTE_SYNC=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            *)
                args+=("$1")
                shift
                ;;
        esac
    done
    # Set remaining args as command args
    COMMAND_ARGS=("${args[@]}")
}

# Validate SSH connection
validate_ssh() {
    echo -e "${BLUE}Validating SSH connection to $REMOTE_HOST...${NC}"

    local ssh_test_opts="$REMOTE_SSH_OPTS -o ConnectTimeout=10 -o BatchMode=yes"

    if [ "$DRY_RUN" = true ]; then
        echo "[DRY-RUN] ssh $ssh_test_opts $REMOTE_HOST 'echo ok'"
        return 0
    fi

    if ! ssh $ssh_test_opts "$REMOTE_HOST" "echo ok" &>/dev/null; then
        echo -e "${RED}Error: Cannot connect to $REMOTE_HOST${NC}"
        echo ""
        echo -e "${YELLOW}Troubleshooting:${NC}"
        echo "  1. Ensure SSH key is configured (password auth not supported)"
        echo "  2. Test connection: ssh $REMOTE_HOST"
        echo "  3. Verify user has Docker permissions on remote"
        echo "  4. Check firewall allows SSH (port 22)"
        exit 1
    fi
    echo -e "${GREEN}SSH connection validated${NC}"
}

# Validate remote Docker is available
validate_remote_docker() {
    echo -e "${BLUE}Checking Docker on remote...${NC}"

    if [ "$DRY_RUN" = true ]; then
        echo "[DRY-RUN] ssh $REMOTE_HOST 'docker compose version'"
        return 0
    fi

    if ! ssh $REMOTE_SSH_OPTS "$REMOTE_HOST" "docker compose version" &>/dev/null; then
        echo -e "${RED}Error: Docker Compose not available on $REMOTE_HOST${NC}"
        echo ""
        echo -e "${YELLOW}Ensure Docker and Docker Compose are installed:${NC}"
        echo "  ssh $REMOTE_HOST 'docker --version && docker compose version'"
        exit 1
    fi
    echo -e "${GREEN}Docker available on remote${NC}"
}

# Sync project files to remote
sync_to_remote() {
    if [ "$REMOTE_SYNC" != "true" ]; then
        return
    fi

    echo -e "${MAGENTA}Syncing project to $REMOTE_HOST:$REMOTE_PATH...${NC}"

    # Build rsync command with excludes
    local rsync_cmd="rsync -avz --delete"
    rsync_cmd+=" --exclude='.git'"
    rsync_cmd+=" --exclude='node_modules'"
    rsync_cmd+=" --exclude='.next'"
    rsync_cmd+=" --exclude='__pycache__'"
    rsync_cmd+=" --exclude='.venv'"
    rsync_cmd+=" --exclude='*.pyc'"
    rsync_cmd+=" --exclude='.env'"
    rsync_cmd+=" --exclude='.docker-remote.env'"
    rsync_cmd+=" --exclude='backend/data/*.db'"
    rsync_cmd+=" --exclude='backend/data/*.db-*'"
    rsync_cmd+=" --exclude='.pytest_cache'"
    rsync_cmd+=" --exclude='.mypy_cache'"
    rsync_cmd+=" --exclude='coverage'"
    rsync_cmd+=" --exclude='.coverage'"

    if [ "$DRY_RUN" = true ]; then
        echo "[DRY-RUN] $rsync_cmd $PROJECT_ROOT/ $REMOTE_HOST:$REMOTE_PATH/"
        return 0
    fi

    # Ensure remote directory exists
    ssh $REMOTE_SSH_OPTS "$REMOTE_HOST" "mkdir -p $REMOTE_PATH"

    # Run rsync
    eval "$rsync_cmd \"$PROJECT_ROOT/\" \"$REMOTE_HOST:$REMOTE_PATH/\""

    echo -e "${GREEN}Sync complete${NC}"
}

# Execute command on remote
remote_exec() {
    local cmd="$1"
    local needs_tty="${2:-false}"

    local ssh_opts="$REMOTE_SSH_OPTS"
    if [ "$needs_tty" = true ]; then
        ssh_opts+=" -t"
    fi

    local full_cmd="cd $REMOTE_PATH && $cmd"

    if [ "$DRY_RUN" = true ]; then
        echo "[DRY-RUN] ssh $ssh_opts $REMOTE_HOST \"$full_cmd\""
        return 0
    fi

    ssh $ssh_opts "$REMOTE_HOST" "$full_cmd"
}

# Print remote banner
print_remote_banner() {
    echo ""
    echo -e "${MAGENTA}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${MAGENTA}║  ${NC}${YELLOW}REMOTE MODE${NC}${MAGENTA}                                               ║${NC}"
    echo -e "${MAGENTA}║  ${NC}Host: ${GREEN}$REMOTE_HOST${NC}"
    echo -e "${MAGENTA}║  ${NC}Path: ${BLUE}$REMOTE_PATH${NC}"
    if [ "$REMOTE_SYNC" = true ]; then
        echo -e "${MAGENTA}║  ${NC}Sync: ${GREEN}enabled${NC}"
    fi
    if [ "$DRY_RUN" = true ]; then
        echo -e "${MAGENTA}║  ${NC}Mode: ${YELLOW}DRY-RUN (no changes will be made)${NC}"
    fi
    echo -e "${MAGENTA}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# Execute docker compose command (local or remote)
docker_compose_cmd() {
    local cmd="docker compose -f $COMPOSE_FILE $*"

    if [ -n "$REMOTE_HOST" ]; then
        remote_exec "$cmd"
    else
        cd "$PROJECT_ROOT"
        if [ "$DRY_RUN" = true ]; then
            echo "[DRY-RUN] $cmd"
        else
            eval "$cmd"
        fi
    fi
}

# Execute docker compose command requiring TTY (interactive shells)
docker_compose_tty() {
    local cmd="docker compose -f $COMPOSE_FILE $*"

    if [ -n "$REMOTE_HOST" ]; then
        remote_exec "$cmd" true
    else
        cd "$PROJECT_ROOT"
        if [ "$DRY_RUN" = true ]; then
            echo "[DRY-RUN] $cmd"
        else
            eval "$cmd"
        fi
    fi
}

show_help() {
    echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║  ${NC}${GREEN}OpenCitiVibes Docker Development Tool${NC}${CYAN}                     ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "Usage: ./scripts/docker-dev.sh [options] [command]"
    echo ""
    echo -e "${YELLOW}Options:${NC}"
    echo "  --remote [user@host]  Execute on remote VM"
    echo "                        If no host provided, uses .docker-remote.env"
    echo "  --sync                Sync project files to remote before command"
    echo "  --dry-run             Show commands without executing"
    echo ""
    echo -e "${YELLOW}Commands:${NC}"
    echo -e "  ${GREEN}up [instance]${NC}       Start dev environment (optionally specify instance)"
    echo -e "  ${GREEN}up-mobile [instance]${NC} Start with local network access"
    echo -e "  ${GREEN}instances${NC}   List available instances"
    echo -e "  ${GREEN}switch${NC}      Switch to a different instance"
    echo -e "  ${GREEN}down${NC}        Stop development environment"
    echo -e "  ${GREEN}restart${NC}     Restart all services"
    echo -e "  ${GREEN}logs${NC}        Follow logs from all services"
    echo -e "  ${GREEN}logs-b${NC}      Follow logs from backend only"
    echo -e "  ${GREEN}logs-f${NC}      Follow logs from frontend only"
    echo -e "  ${GREEN}logs-n${NC}      Follow logs from ntfy only"
    echo -e "  ${GREEN}backend${NC}     Open shell in backend container"
    echo -e "  ${GREEN}frontend${NC}    Open shell in frontend container"
    echo -e "  ${GREEN}db-init${NC}     Initialize database (categories + admin)"
    echo -e "  ${GREEN}db-reset${NC}    Reset database to empty state"
    echo -e "  ${GREEN}db-seed${NC}     Seed database with test data"
    echo -e "  ${GREEN}db-migrate${NC}  Run Alembic migrations"
    echo -e "  ${GREEN}test${NC}        Run all tests"
    echo -e "  ${GREEN}test-b${NC}      Run backend tests only"
    echo -e "  ${GREEN}test-f${NC}      Run frontend lint only"
    echo -e "  ${GREEN}build${NC}       Rebuild containers"
    echo -e "  ${GREEN}clean${NC}       Remove containers and volumes"
    echo -e "  ${GREEN}status${NC}      Show container status"
    echo -e "  ${GREEN}ps${NC}          Alias for status"
    echo ""
    echo -e "${YELLOW}Instance Examples:${NC}"
    echo "  ./scripts/docker-dev.sh instances          # List available instances"
    echo "  ./scripts/docker-dev.sh up montreal        # Start with Montreal instance"
    echo "  ./scripts/docker-dev.sh up quebec          # Start with Quebec instance"
    echo "  ./scripts/docker-dev.sh switch calgary     # Switch to Calgary (restarts)"
    echo ""
    echo -e "${YELLOW}Local Examples:${NC}"
    echo "  ./scripts/docker-dev.sh up"
    echo "  ./scripts/docker-dev.sh logs"
    echo "  ./scripts/docker-dev.sh backend"
    echo ""
    echo -e "${YELLOW}Remote Examples:${NC}"
    echo "  ./scripts/docker-dev.sh --remote matt@192.168.1.100 up"
    echo "  ./scripts/docker-dev.sh --remote up              # Uses .docker-remote.env"
    echo "  ./scripts/docker-dev.sh --remote --sync build    # Sync files then build"
    echo "  ./scripts/docker-dev.sh --remote --dry-run up    # Preview SSH commands"
}

check_env() {
    if [ -n "$REMOTE_HOST" ]; then
        # Check remote .env
        if [ "$DRY_RUN" = true ]; then
            echo "[DRY-RUN] Checking remote .env file"
            return 0
        fi
        if ! ssh $REMOTE_SSH_OPTS "$REMOTE_HOST" "test -f $REMOTE_PATH/.env"; then
            echo -e "${YELLOW}Warning: .env file not found on remote. Checking for .env.example...${NC}"
            if ssh $REMOTE_SSH_OPTS "$REMOTE_HOST" "test -f $REMOTE_PATH/.env.example"; then
                echo -e "${YELLOW}Creating .env from .env.example on remote...${NC}"
                ssh $REMOTE_SSH_OPTS "$REMOTE_HOST" "cp $REMOTE_PATH/.env.example $REMOTE_PATH/.env"
                echo -e "${GREEN}Created .env file on remote. Please SSH and update values.${NC}"
            else
                echo -e "${RED}Error: Neither .env nor .env.example found on remote${NC}"
                exit 1
            fi
        fi
    else
        # Check local .env
        if [ ! -f "$PROJECT_ROOT/.env" ]; then
            echo -e "${YELLOW}Warning: .env file not found. Creating from .env.example...${NC}"
            if [ -f "$PROJECT_ROOT/.env.example" ]; then
                cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
                echo -e "${GREEN}Created .env file. Please review and update values.${NC}"
            else
                echo -e "${RED}Error: .env.example not found${NC}"
                exit 1
            fi
        fi
    fi
}

# Initialize remote connection (validate + optional sync)
init_remote() {
    if [ -n "$REMOTE_HOST" ]; then
        print_remote_banner
        validate_ssh
        validate_remote_docker
        sync_to_remote
    fi
}

# Load environment
load_env

# Parse arguments first
parse_args "$@"

# Main command handler
case "${COMMAND_ARGS[0]:-help}" in
    up)
        # Check if instance is specified as second argument
        force_recreate=""
        if [ -n "${COMMAND_ARGS[1]}" ]; then
            switch_instance "${COMMAND_ARGS[1]}"
            force_recreate="--force-recreate"
            echo ""
        fi

        init_remote
        check_env

        # Show current instance
        current_instance=$(cat "$PROJECT_ROOT/.active-instance" 2>/dev/null || echo "unknown")
        echo -e "${GREEN}Starting development environment...${NC}"
        echo -e "  Instance: ${CYAN}$current_instance${NC}"
        echo ""

        docker_compose_cmd "up -d --build $force_recreate"
        echo ""
        if [ -n "$REMOTE_HOST" ]; then
            remote_hostname="${REMOTE_HOST#*@}"
            echo -e "${GREEN}Services started on remote:${NC}"
            echo -e "  Frontend: ${BLUE}http://$remote_hostname:3000${NC}"
            echo -e "  Backend:  ${BLUE}http://$remote_hostname:8000${NC}"
            echo -e "  API Docs: ${BLUE}http://$remote_hostname:8000/docs${NC}"
        else
            echo -e "${GREEN}Services started:${NC}"
            echo -e "  Frontend: ${BLUE}http://localhost:3000${NC}"
            echo -e "  Backend:  ${BLUE}http://localhost:8000${NC}"
            echo -e "  API Docs: ${BLUE}http://localhost:8000/docs${NC}"
            echo -e "  Ntfy:     ${BLUE}http://localhost:8080${NC}"
        fi
        echo ""
        echo -e "Run ${YELLOW}./scripts/docker-dev.sh logs${NC} to follow logs"
        echo -e "Subscribe to notifications: ${CYAN}http://localhost:8080/dev-admin-ideas${NC}"
        ;;

    up-mobile)
        # Check if instance is specified as second argument
        force_recreate=""
        if [ -n "${COMMAND_ARGS[1]}" ]; then
            switch_instance "${COMMAND_ARGS[1]}"
            force_recreate="--force-recreate"
            echo ""
        fi

        init_remote
        check_env

        # Auto-detect host IP for local network access
        if [ -z "$REMOTE_HOST" ]; then
            # Get local IP (works on Linux and macOS)
            HOST_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || ipconfig getifaddr en0 2>/dev/null || echo "localhost")
            if [ "$HOST_IP" = "" ] || [ "$HOST_IP" = "localhost" ]; then
                echo -e "${YELLOW}Warning: Could not detect local IP. Using localhost.${NC}"
                HOST_IP="localhost"
            fi
            export HOST_IP
            echo -e "${MAGENTA}Mobile testing mode enabled${NC}"
            echo -e "  Host IP: ${GREEN}$HOST_IP${NC}"
            echo ""
        fi

        echo -e "${GREEN}Starting development environment for mobile testing...${NC}"
        docker_compose_cmd "up -d --build $force_recreate"
        echo ""
        if [ -n "$REMOTE_HOST" ]; then
            remote_hostname="${REMOTE_HOST#*@}"
            echo -e "${GREEN}Services started on remote:${NC}"
            echo -e "  Frontend: ${BLUE}http://$remote_hostname:3000${NC}"
            echo -e "  Backend:  ${BLUE}http://$remote_hostname:8000${NC}"
            echo -e "  API Docs: ${BLUE}http://$remote_hostname:8000/docs${NC}"
        else
            echo -e "${GREEN}Services accessible on local network:${NC}"
            echo -e "  Frontend: ${BLUE}http://$HOST_IP:3000${NC}"
            echo -e "  Backend:  ${BLUE}http://$HOST_IP:8000${NC}"
            echo -e "  API Docs: ${BLUE}http://$HOST_IP:8000/docs${NC}"
            echo -e "  Ntfy:     ${BLUE}http://$HOST_IP:8080${NC}"
            echo ""
            echo -e "${YELLOW}On your mobile device, open: http://$HOST_IP:3000${NC}"
        fi
        echo ""
        echo -e "Run ${YELLOW}./scripts/docker-dev.sh logs${NC} to follow logs"
        echo -e "Subscribe to notifications: ${CYAN}http://localhost:8080/dev-admin-ideas${NC}"
        ;;

    down)
        init_remote
        echo -e "${YELLOW}Stopping development environment...${NC}"
        docker_compose_cmd "down"
        echo -e "${GREEN}Done${NC}"
        ;;

    restart)
        init_remote
        echo -e "${YELLOW}Restarting services...${NC}"
        docker_compose_cmd "restart"
        echo -e "${GREEN}Done${NC}"
        ;;

    logs)
        init_remote
        docker_compose_cmd "logs -f"
        ;;

    logs-b|logs-backend)
        init_remote
        docker_compose_cmd "logs -f backend"
        ;;

    logs-f|logs-frontend)
        init_remote
        docker_compose_cmd "logs -f frontend"
        ;;

    logs-n|logs-ntfy)
        init_remote
        docker_compose_cmd "logs -f ntfy"
        ;;

    backend|shell-b)
        init_remote
        echo -e "${BLUE}Opening shell in backend container...${NC}"
        docker_compose_tty "exec backend bash"
        ;;

    frontend|shell-f)
        init_remote
        echo -e "${BLUE}Opening shell in frontend container...${NC}"
        docker_compose_tty "exec frontend sh"
        ;;

    db-init)
        init_remote
        echo -e "${YELLOW}Initializing database (categories + admin)...${NC}"
        docker_compose_cmd "exec backend python init_db.py"
        echo -e "${GREEN}Database initialized${NC}"
        ;;

    db-reset)
        init_remote
        echo -e "${YELLOW}Resetting database...${NC}"
        docker_compose_cmd "exec backend python -c \"
from repositories.database import engine, Base
from repositories.db_models import *
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)
print('Database reset complete')
\""
        echo -e "${GREEN}Database reset complete${NC}"
        ;;

    db-seed)
        init_remote
        echo -e "${YELLOW}Seeding database with test data...${NC}"
        docker_compose_cmd "exec backend python scripts/seed_data.py"
        echo -e "${GREEN}Database seeded${NC}"
        ;;

    db-migrate)
        init_remote
        echo -e "${YELLOW}Running Alembic migrations...${NC}"
        docker_compose_cmd "exec backend alembic upgrade head"
        echo -e "${GREEN}Migrations complete${NC}"
        ;;

    test)
        init_remote
        echo -e "${BLUE}Running backend tests...${NC}"
        docker_compose_cmd "exec backend pytest --cov=. --cov-report=term-missing -v"
        echo ""
        echo -e "${BLUE}Running frontend lint...${NC}"
        docker_compose_cmd "exec frontend pnpm lint"
        echo ""
        echo -e "${BLUE}Running frontend type check...${NC}"
        docker_compose_cmd "exec frontend pnpm exec tsc --noEmit"
        echo -e "${GREEN}All tests complete${NC}"
        ;;

    test-b|test-backend)
        init_remote
        echo -e "${BLUE}Running backend tests...${NC}"
        docker_compose_cmd "exec backend pytest --cov=. --cov-report=term-missing -v"
        ;;

    test-f|test-frontend)
        init_remote
        echo -e "${BLUE}Running frontend lint...${NC}"
        docker_compose_cmd "exec frontend pnpm lint"
        echo ""
        echo -e "${BLUE}Running frontend type check...${NC}"
        docker_compose_cmd "exec frontend pnpm exec tsc --noEmit"
        ;;

    build)
        init_remote
        echo -e "${YELLOW}Rebuilding containers...${NC}"
        docker_compose_cmd "build --no-cache"
        echo -e "${GREEN}Build complete${NC}"
        ;;

    clean)
        init_remote
        echo -e "${RED}This will remove all containers and volumes!${NC}"
        if [ -n "$REMOTE_HOST" ]; then
            echo -e "${RED}Target: $REMOTE_HOST${NC}"
        fi
        read -p "Are you sure? (y/N): " confirm
        if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
            docker_compose_cmd "down -v --remove-orphans"
            if [ -n "$REMOTE_HOST" ]; then
                remote_exec "docker image prune -f"
            else
                docker image prune -f
            fi
            echo -e "${GREEN}Cleanup complete${NC}"
        else
            echo "Aborted"
        fi
        ;;

    status|ps)
        init_remote
        docker_compose_cmd "ps"
        ;;

    instances|list)
        show_instances
        ;;

    switch)
        if [ -z "${COMMAND_ARGS[1]}" ]; then
            echo -e "${RED}Error: Please specify an instance${NC}"
            echo ""
            show_instances
            exit 1
        fi

        # Stop current containers BEFORE switching (uses old project name)
        was_running=false
        # Check if any dev containers are running on our ports
        running_containers=$(docker ps --format '{{.Names}}' | grep -E '(idees|ideas|ocv).*-dev$' || true)
        if [ -n "$running_containers" ]; then
            was_running=true
            echo -e "${YELLOW}Stopping current containers...${NC}"
            # Stop and remove containers directly (docker-compose won't see them after project name change)
            echo "$running_containers" | xargs -r docker stop 2>/dev/null || true
            echo "$running_containers" | xargs -r docker rm 2>/dev/null || true
            # Clean up network
            docker network ls --format '{{.Name}}' | grep -E '(idees|ideas|ocv).*-dev-network$' | xargs -r docker network rm 2>/dev/null || true
            echo ""
        fi

        # Switch instance (updates .env with new project name)
        switch_instance "${COMMAND_ARGS[1]}"

        # Reload environment after switch
        load_env

        # Start containers with new instance if they were running before
        if [ "$was_running" = true ]; then
            echo ""
            echo -e "${YELLOW}Starting containers with new instance...${NC}"
            docker_compose_cmd "up -d --build --force-recreate"
            echo ""
            echo -e "${GREEN}Services started with ${CYAN}${COMMAND_ARGS[1]}${GREEN} instance${NC}"
            echo -e "  Frontend: ${BLUE}http://localhost:3000${NC}"
            echo -e "  Backend:  ${BLUE}http://localhost:8000${NC}"
            echo -e "  Ntfy:     ${BLUE}http://localhost:8080${NC}"
        fi
        ;;

    help|--help|-h)
        show_help
        ;;

    *)
        echo -e "${RED}Unknown command: ${COMMAND_ARGS[0]}${NC}"
        echo ""
        show_help
        exit 1
        ;;
esac
