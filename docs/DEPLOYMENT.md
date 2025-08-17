# BSE Data Optimization - Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying the BSE Data Optimization system across different environments. The system uses Docker containers orchestrated with Docker Compose for consistent deployments.

## Prerequisites

### System Requirements

**Minimum Requirements:**
- CPU: 2 cores
- RAM: 4GB
- Storage: 20GB SSD
- Network: 100 Mbps

**Recommended Requirements:**
- CPU: 4+ cores
- RAM: 8GB+
- Storage: 50GB+ SSD
- Network: 1 Gbps

### Software Dependencies

**Required Software:**
- Docker 20.10+
- Docker Compose 2.0+
- Git 2.30+
- curl (for health checks)

**Optional Tools:**
- Make (for build automation)
- jq (for JSON processing)
- htop (for system monitoring)

### Installation Commands

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y docker.io docker-compose git curl make jq htop

# CentOS/RHEL
sudo yum install -y docker docker-compose git curl make jq htop

# macOS (with Homebrew)
brew install docker docker-compose git curl make jq htop

# Start Docker service
sudo systemctl start docker
sudo systemctl enable docker

# Add user to docker group
sudo usermod -aG docker $USER
```

## Environment Configuration

### Environment Files

The system uses environment-specific configuration files:

- `.env.development` - Development environment
- `.env.staging` - Staging environment  
- `.env.production` - Production environment

### Required Environment Variables

```bash
# Application Settings
FLASK_ENV=production
LOG_LEVEL=INFO
DEBUG=false

# Redis Configuration
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=your_secure_password

# BSE API Configuration
BSE_API_KEY=your_bse_api_key
BSE_API_BASE_URL=https://api.bseindia.com

# Security Settings
SECRET_KEY=your_secure_secret_key
CORS_ORIGINS=https://yourdomain.com

# Performance Settings
WEBSOCKET_MAX_CONNECTIONS=500
CACHE_BATCH_SIZE=50
BATCH_FETCH_INTERVAL=3
```

### Secrets Management

**For Production:**
```bash
# Create secrets directory
mkdir -p /etc/bse-secrets

# Store sensitive values
echo "your_bse_api_key" > /etc/bse-secrets/bse_api_key
echo "your_redis_password" > /etc/bse-secrets/redis_password
echo "your_secret_key" > /etc/bse-secrets/secret_key

# Set proper permissions
chmod 600 /etc/bse-secrets/*
chown root:root /etc/bse-secrets/*
```

## Deployment Methods

### Method 1: Automated Deployment Script

The recommended deployment method using the provided script:

```bash
# Clone repository
git clone https://github.com/your-org/bse-data-optimization.git
cd bse-data-optimization

# Make deployment script executable
chmod +x deployment/deploy.sh

# Deploy to development
./deployment/deploy.sh development

# Deploy to staging
./deployment/deploy.sh staging

# Deploy to production
./deployment/deploy.sh production v1.2.0
```

### Method 2: Manual Docker Compose

For manual control over the deployment process:

```bash
# Navigate to deployment directory
cd deployment

# Copy environment configuration
cp .env.production .env

# Build and start services
docker-compose build
docker-compose up -d

# Verify deployment
docker-compose ps
docker-compose logs -f
```

### Method 3: Kubernetes Deployment

For production Kubernetes environments:

```bash
# Apply Kubernetes manifests
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/redis.yaml
kubectl apply -f k8s/backend.yaml
kubectl apply -f k8s/frontend.yaml
kubectl apply -f k8s/monitoring.yaml
kubectl apply -f k8s/ingress.yaml

# Verify deployment
kubectl get pods -n bse-system
kubectl get services -n bse-system
```

## Service Configuration

### Redis Configuration

**redis.conf:**
```conf
# Memory management
maxmemory 2gb
maxmemory-policy allkeys-lru

# Persistence
save 900 1
save 300 10
save 60 10000

# Security
requirepass your_redis_password
bind 0.0.0.0
protected-mode yes

# Performance
tcp-keepalive 300
timeout 0
```

### Nginx Configuration

**nginx.conf:**
```nginx
upstream backend {
    server bse-backend:5000;
}

upstream frontend {
    server bse-frontend:80;
}

upstream monitoring {
    server bse-monitoring:8080;
}

server {
    listen 80;
    server_name yourdomain.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;
    
    # SSL Configuration
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    
    # Frontend
    location / {
        proxy_pass http://frontend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    # Backend API
    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 60s;
    }
    
    # WebSocket
    location /socket.io/ {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    # Monitoring Dashboard
    location /monitoring/ {
        proxy_pass http://monitoring/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        
        # Basic auth for monitoring
        auth_basic "Monitoring Dashboard";
        auth_basic_user_file /etc/nginx/.htpasswd;
    }
}
```

## Health Checks and Monitoring

### Service Health Checks

Each service includes built-in health check endpoints:

```bash
# Backend health check
curl -f http://localhost:5000/health

# Frontend health check  
curl -f http://localhost:8080/

# Monitoring dashboard health check
curl -f http://localhost:8081/api/health

# Redis health check
redis-cli ping
```

### Monitoring Setup

**Prometheus Configuration:**
```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'bse-backend'
    static_configs:
      - targets: ['bse-backend:5000']
    metrics_path: '/metrics'
    
  - job_name: 'bse-monitoring'
    static_configs:
      - targets: ['bse-monitoring:8080']
    metrics_path: '/api/metrics'
```

**Grafana Dashboard:**
- Import dashboard from `monitoring/grafana-dashboard.json`
- Configure data source: Prometheus
- Set up alerting rules for critical metrics

### Log Management

**Log Configuration:**
```yaml
# docker-compose.yml logging section
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

**Centralized Logging with ELK Stack:**
```bash
# Start ELK stack
docker-compose -f elk-stack.yml up -d

# Configure Filebeat
filebeat -e -c filebeat.yml
```

## Deployment Verification

### Automated Verification

The deployment includes an automated verification script:

```bash
# Run verification tests
python deployment/verify_deployment.py

# Expected output:
# ✅ PASS Backend Health Check
# ✅ PASS Individual Stock Quote API  
# ✅ PASS Batch Stock Quotes API
# ✅ PASS Frontend Accessibility
# ✅ PASS WebSocket Connectivity
# ✅ PASS Cache Functionality
# ✅ PASS Monitoring Dashboard
# ✅ PASS Performance Benchmarks
```

### Manual Verification Steps

1. **Service Status Check:**
```bash
docker-compose ps
# All services should show "Up (healthy)"
```

2. **API Functionality:**
```bash
# Test individual stock quote
curl "http://localhost:5000/api/stock/500325"

# Test batch quotes
curl "http://localhost:5000/api/stocks/batch?symbols=500325,500209"

# Test market status
curl "http://localhost:5000/api/market/status"
```

3. **WebSocket Connectivity:**
```bash
# Use wscat to test WebSocket
npm install -g wscat
wscat -c ws://localhost:5000/socket.io/?EIO=4&transport=websocket
```

4. **Performance Testing:**
```bash
# Run load test
cd tests/performance
python load_test.py --users 50 --spawn-rate 5 --run-time 60s
```

## Troubleshooting

### Common Issues

**1. Service Won't Start**
```bash
# Check logs
docker-compose logs service-name

# Common causes:
# - Port conflicts
# - Missing environment variables
# - Insufficient resources
# - Network connectivity issues
```

**2. Redis Connection Issues**
```bash
# Check Redis status
docker-compose exec redis redis-cli ping

# Check Redis logs
docker-compose logs redis

# Verify Redis configuration
docker-compose exec redis cat /usr/local/etc/redis/redis.conf
```

**3. High Memory Usage**
```bash
# Check container resource usage
docker stats

# Check Redis memory usage
docker-compose exec redis redis-cli info memory

# Optimize Redis memory
docker-compose exec redis redis-cli config set maxmemory-policy allkeys-lru
```

**4. WebSocket Connection Failures**
```bash
# Check WebSocket logs
docker-compose logs bse-backend | grep -i websocket

# Verify WebSocket endpoint
curl -I http://localhost:5000/socket.io/

# Check firewall rules
sudo ufw status
```

### Performance Issues

**1. Slow API Response Times**
```bash
# Check cache hit rates
curl http://localhost:8081/api/metrics/current | jq '.application.cache_hit_rate'

# Monitor Redis performance
docker-compose exec redis redis-cli --latency

# Check system resources
htop
```

**2. High CPU Usage**
```bash
# Identify resource-intensive processes
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# Scale services if needed
docker-compose up -d --scale bse-backend=3
```

### Recovery Procedures

**1. Service Recovery**
```bash
# Restart individual service
docker-compose restart service-name

# Restart all services
docker-compose restart

# Force recreate containers
docker-compose up -d --force-recreate
```

**2. Data Recovery**
```bash
# Restore Redis data from backup
docker-compose exec redis redis-cli flushall
docker cp backup/redis-data.rdb $(docker-compose ps -q redis):/data/dump.rdb
docker-compose restart redis
```

**3. Rollback Deployment**
```bash
# Rollback to previous version
./deployment/deploy.sh rollback

# Manual rollback
docker tag bse-backend:previous bse-backend:latest
docker-compose up -d
```

## Security Considerations

### SSL/TLS Configuration

**Generate SSL Certificates:**
```bash
# Self-signed certificate (development)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout deployment/ssl/key.pem \
  -out deployment/ssl/cert.pem

# Let's Encrypt certificate (production)
certbot certonly --standalone -d yourdomain.com
```

### Firewall Configuration

**UFW Rules:**
```bash
# Allow SSH
sudo ufw allow 22

# Allow HTTP/HTTPS
sudo ufw allow 80
sudo ufw allow 443

# Allow specific application ports (if needed)
sudo ufw allow from trusted_ip to any port 5000
sudo ufw allow from trusted_ip to any port 6379

# Enable firewall
sudo ufw enable
```

### Security Hardening

**Docker Security:**
```bash
# Run containers as non-root user
# Use read-only filesystems where possible
# Limit container capabilities
# Use security scanning tools

# Example security scan
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image bse-backend:latest
```

## Backup and Recovery

### Automated Backup Script

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backups/bse-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Backup Redis data
docker-compose exec redis redis-cli bgsave
docker cp $(docker-compose ps -q redis):/data/dump.rdb "$BACKUP_DIR/"

# Backup application logs
docker-compose logs > "$BACKUP_DIR/application.log"

# Backup configuration
cp -r deployment/ "$BACKUP_DIR/"

# Compress backup
tar -czf "$BACKUP_DIR.tar.gz" "$BACKUP_DIR"
rm -rf "$BACKUP_DIR"

echo "Backup completed: $BACKUP_DIR.tar.gz"
```

### Backup Schedule

**Crontab Entry:**
```bash
# Daily backup at 2 AM
0 2 * * * /path/to/backup.sh

# Weekly full backup
0 2 * * 0 /path/to/full-backup.sh
```

## Scaling and Performance Optimization

### Horizontal Scaling

**Scale Backend Services:**
```bash
# Scale to 3 backend instances
docker-compose up -d --scale bse-backend=3

# Update load balancer configuration
# Add health checks for new instances
```

**Redis Clustering:**
```yaml
# redis-cluster.yml
version: '3.8'
services:
  redis-master:
    image: redis:7-alpine
    command: redis-server --port 6379
    
  redis-slave-1:
    image: redis:7-alpine
    command: redis-server --port 6379 --slaveof redis-master 6379
    
  redis-slave-2:
    image: redis:7-alpine
    command: redis-server --port 6379 --slaveof redis-master 6379
```

### Performance Tuning

**System Optimization:**
```bash
# Increase file descriptor limits
echo "* soft nofile 65536" >> /etc/security/limits.conf
echo "* hard nofile 65536" >> /etc/security/limits.conf

# Optimize network settings
echo "net.core.somaxconn = 65535" >> /etc/sysctl.conf
echo "net.ipv4.tcp_max_syn_backlog = 65535" >> /etc/sysctl.conf
sysctl -p
```

**Application Optimization:**
```python
# gunicorn.conf.py
bind = "0.0.0.0:5000"
workers = 4
worker_class = "gevent"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
preload_app = True
```

## Maintenance Procedures

### Regular Maintenance Tasks

**Daily:**
- Check service health status
- Monitor resource usage
- Review error logs
- Verify backup completion

**Weekly:**
- Update security patches
- Clean up old logs and backups
- Performance analysis
- Capacity planning review

**Monthly:**
- Full system backup
- Security audit
- Performance optimization
- Documentation updates

### Update Procedures

**Application Updates:**
```bash
# Pull latest code
git pull origin main

# Build new images
docker-compose build

# Deploy with zero downtime
./deployment/deploy.sh production v1.3.0

# Verify deployment
python deployment/verify_deployment.py
```

**Security Updates:**
```bash
# Update base images
docker pull python:3.9-slim
docker pull redis:7-alpine
docker pull nginx:alpine

# Rebuild with updated base images
docker-compose build --no-cache

# Deploy updates
docker-compose up -d
```

This deployment guide provides comprehensive instructions for deploying and maintaining the BSE Data Optimization system across different environments with proper security, monitoring, and backup procedures.