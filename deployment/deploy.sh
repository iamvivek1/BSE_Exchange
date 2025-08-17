#!/bin/bash

# BSE Data Optimization Deployment Script
# This script handles deployment to different environments

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV="${1:-development}"
VERSION="${2:-latest}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed or not in PATH"
        exit 1
    fi
    
    # Check environment file
    if [[ ! -f "$SCRIPT_DIR/.env.$ENV" ]]; then
        log_error "Environment file .env.$ENV not found"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Load environment configuration
load_environment() {
    log_info "Loading environment configuration for: $ENV"
    
    # Copy environment file
    cp "$SCRIPT_DIR/.env.$ENV" "$SCRIPT_DIR/.env"
    
    # Source environment variables
    set -a
    source "$SCRIPT_DIR/.env"
    set +a
    
    log_success "Environment configuration loaded"
}

# Run pre-deployment tests
run_tests() {
    log_info "Running pre-deployment tests..."
    
    cd "$PROJECT_ROOT"
    
    # Backend tests
    log_info "Running backend tests..."
    python -m pytest tests/ -v --tb=short || {
        log_error "Backend tests failed"
        exit 1
    }
    
    # Frontend tests
    log_info "Running frontend tests..."
    npm test || {
        log_error "Frontend tests failed"
        exit 1
    }
    
    log_success "All tests passed"
}

# Build Docker images
build_images() {
    log_info "Building Docker images..."
    
    cd "$SCRIPT_DIR"
    
    # Build with version tag
    docker-compose build --build-arg VERSION="$VERSION"
    
    # Tag images with version
    docker tag "bse-backend:latest" "bse-backend:$VERSION"
    docker tag "bse-frontend:latest" "bse-frontend:$VERSION"
    docker tag "bse-monitoring:latest" "bse-monitoring:$VERSION"
    
    log_success "Docker images built successfully"
}

# Deploy services
deploy_services() {
    log_info "Deploying services..."
    
    cd "$SCRIPT_DIR"
    
    # Stop existing services
    docker-compose down --remove-orphans
    
    # Start services
    docker-compose up -d
    
    # Wait for services to be healthy
    log_info "Waiting for services to be healthy..."
    
    local max_attempts=30
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        if docker-compose ps | grep -q "Up (healthy)"; then
            log_success "Services are healthy"
            break
        fi
        
        if [[ $attempt -eq $max_attempts ]]; then
            log_error "Services failed to become healthy within timeout"
            docker-compose logs
            exit 1
        fi
        
        log_info "Attempt $attempt/$max_attempts - waiting for services..."
        sleep 10
        ((attempt++))
    done
    
    log_success "Services deployed successfully"
}

# Run post-deployment verification
verify_deployment() {
    log_info "Running post-deployment verification..."
    
    # Check backend health
    local backend_url="http://localhost:5000"
    if curl -f "$backend_url/health" &> /dev/null; then
        log_success "Backend health check passed"
    else
        log_error "Backend health check failed"
        exit 1
    fi
    
    # Check frontend
    local frontend_url="http://localhost:8080"
    if curl -f "$frontend_url" &> /dev/null; then
        log_success "Frontend health check passed"
    else
        log_error "Frontend health check failed"
        exit 1
    fi
    
    # Check monitoring dashboard
    local monitoring_url="http://localhost:8081"
    if curl -f "$monitoring_url/api/health" &> /dev/null; then
        log_success "Monitoring dashboard health check passed"
    else
        log_warning "Monitoring dashboard health check failed (non-critical)"
    fi
    
    # Run basic API tests
    log_info "Running basic API tests..."
    python "$SCRIPT_DIR/verify_deployment.py" || {
        log_error "API verification tests failed"
        exit 1
    }
    
    log_success "Deployment verification completed"
}

# Rollback deployment
rollback_deployment() {
    log_warning "Rolling back deployment..."
    
    cd "$SCRIPT_DIR"
    
    # Stop current services
    docker-compose down
    
    # Restore previous version (if available)
    if docker images | grep -q "bse-backend:previous"; then
        docker tag "bse-backend:previous" "bse-backend:latest"
        docker tag "bse-frontend:previous" "bse-frontend:latest"
        docker tag "bse-monitoring:previous" "bse-monitoring:latest"
        
        # Restart services
        docker-compose up -d
        
        log_success "Rollback completed"
    else
        log_error "No previous version available for rollback"
        exit 1
    fi
}

# Cleanup old images
cleanup() {
    log_info "Cleaning up old Docker images..."
    
    # Remove dangling images
    docker image prune -f
    
    # Remove old versions (keep last 3)
    docker images --format "table {{.Repository}}:{{.Tag}}" | \
        grep -E "bse-(backend|frontend|monitoring)" | \
        tail -n +4 | \
        xargs -r docker rmi
    
    log_success "Cleanup completed"
}

# Main deployment function
main() {
    log_info "Starting BSE Data Optimization deployment"
    log_info "Environment: $ENV"
    log_info "Version: $VERSION"
    
    # Tag current images as previous (for rollback)
    if docker images | grep -q "bse-backend:latest"; then
        docker tag "bse-backend:latest" "bse-backend:previous" || true
        docker tag "bse-frontend:latest" "bse-frontend:previous" || true
        docker tag "bse-monitoring:latest" "bse-monitoring:previous" || true
    fi
    
    # Execute deployment steps
    check_prerequisites
    load_environment
    
    if [[ "$ENV" != "production" ]]; then
        run_tests
    fi
    
    build_images
    deploy_services
    verify_deployment
    cleanup
    
    log_success "Deployment completed successfully!"
    log_info "Services are available at:"
    log_info "  - Backend API: http://localhost:5000"
    log_info "  - Frontend: http://localhost:8080"
    log_info "  - Monitoring: http://localhost:8081"
    log_info "  - Load Balancer: http://localhost"
}

# Handle script arguments
case "${1:-}" in
    "rollback")
        rollback_deployment
        ;;
    "cleanup")
        cleanup
        ;;
    "verify")
        verify_deployment
        ;;
    *)
        main
        ;;
esac