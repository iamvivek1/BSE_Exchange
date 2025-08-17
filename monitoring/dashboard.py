#!/usr/bin/env python3
"""
System health monitoring dashboard for BSE Data Optimization system.
Provides real-time metrics and health status visualization.
"""

import time
import json
import redis
import psutil
from flask import Flask, render_template, jsonify
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Dict, List, Any
import threading
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from services.monitoring_service import MonitoringService


@dataclass
class SystemMetrics:
    """System performance metrics"""
    timestamp: str
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_total_mb: float
    disk_percent: float
    network_bytes_sent: int
    network_bytes_recv: int
    active_connections: int
    redis_memory_mb: float
    redis_connected_clients: int


@dataclass
class ApplicationMetrics:
    """Application-specific metrics"""
    timestamp: str
    api_requests_per_minute: int
    websocket_connections: int
    cache_hit_rate: float
    avg_response_time_ms: float
    error_rate_percent: float
    batch_fetch_success_rate: float
    active_stock_symbols: int


class HealthMonitor:
    """System health monitoring service"""
    
    def __init__(self):
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
        self.monitoring_service = MonitoringService()
        self.metrics_history = []
        self.app_metrics_history = []
        self.max_history = 1440  # 24 hours of minute-by-minute data
        self.running = False
        
    def collect_system_metrics(self) -> SystemMetrics:
        """Collect current system performance metrics"""
        # CPU and Memory
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Network
        network = psutil.net_io_counters()
        
        # Active connections
        connections = len(psutil.net_connections())
        
        # Redis metrics
        try:
            redis_info = self.redis_client.info()
            redis_memory_mb = redis_info.get('used_memory', 0) / (1024 * 1024)
            redis_clients = redis_info.get('connected_clients', 0)
        except Exception:
            redis_memory_mb = 0
            redis_clients = 0
        
        return SystemMetrics(
            timestamp=datetime.now().isoformat(),
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_used_mb=memory.used / (1024 * 1024),
            memory_total_mb=memory.total / (1024 * 1024),
            disk_percent=disk.percent,
            network_bytes_sent=network.bytes_sent,
            network_bytes_recv=network.bytes_recv,
            active_connections=connections,
            redis_memory_mb=redis_memory_mb,
            redis_connected_clients=redis_clients
        )
    
    def collect_application_metrics(self) -> ApplicationMetrics:
        """Collect application-specific metrics"""
        try:
            # Get metrics from monitoring service
            metrics = self.monitoring_service.get_current_metrics()
            
            return ApplicationMetrics(
                timestamp=datetime.now().isoformat(),
                api_requests_per_minute=metrics.get('api_requests_per_minute', 0),
                websocket_connections=metrics.get('websocket_connections', 0),
                cache_hit_rate=metrics.get('cache_hit_rate', 0.0),
                avg_response_time_ms=metrics.get('avg_response_time_ms', 0.0),
                error_rate_percent=metrics.get('error_rate_percent', 0.0),
                batch_fetch_success_rate=metrics.get('batch_fetch_success_rate', 100.0),
                active_stock_symbols=metrics.get('active_stock_symbols', 0)
            )
        except Exception as e:
            print(f"Error collecting application metrics: {e}")
            return ApplicationMetrics(
                timestamp=datetime.now().isoformat(),
                api_requests_per_minute=0,
                websocket_connections=0,
                cache_hit_rate=0.0,
                avg_response_time_ms=0.0,
                error_rate_percent=0.0,
                batch_fetch_success_rate=0.0,
                active_stock_symbols=0
            )
    
    def start_monitoring(self):
        """Start continuous monitoring"""
        self.running = True
        
        def monitor_loop():
            while self.running:
                try:
                    # Collect metrics
                    sys_metrics = self.collect_system_metrics()
                    app_metrics = self.collect_application_metrics()
                    
                    # Store in history
                    self.metrics_history.append(sys_metrics)
                    self.app_metrics_history.append(app_metrics)
                    
                    # Limit history size
                    if len(self.metrics_history) > self.max_history:
                        self.metrics_history.pop(0)
                    if len(self.app_metrics_history) > self.max_history:
                        self.app_metrics_history.pop(0)
                    
                    # Store in Redis for persistence
                    self.redis_client.setex(
                        'monitoring:system:latest',
                        300,  # 5 minute TTL
                        json.dumps(asdict(sys_metrics))
                    )
                    self.redis_client.setex(
                        'monitoring:application:latest',
                        300,  # 5 minute TTL
                        json.dumps(asdict(app_metrics))
                    )
                    
                except Exception as e:
                    print(f"Error in monitoring loop: {e}")
                
                time.sleep(60)  # Collect metrics every minute
        
        # Start monitoring in background thread
        monitor_thread = threading.Thread(target=monitor_loop)
        monitor_thread.daemon = True
        monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.running = False
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall system health status"""
        if not self.metrics_history or not self.app_metrics_history:
            return {
                'status': 'unknown',
                'message': 'No metrics available',
                'checks': {}
            }
        
        latest_sys = self.metrics_history[-1]
        latest_app = self.app_metrics_history[-1]
        
        checks = {
            'cpu_usage': {
                'status': 'healthy' if latest_sys.cpu_percent < 80 else 'warning' if latest_sys.cpu_percent < 95 else 'critical',
                'value': latest_sys.cpu_percent,
                'threshold': 80
            },
            'memory_usage': {
                'status': 'healthy' if latest_sys.memory_percent < 80 else 'warning' if latest_sys.memory_percent < 95 else 'critical',
                'value': latest_sys.memory_percent,
                'threshold': 80
            },
            'disk_usage': {
                'status': 'healthy' if latest_sys.disk_percent < 85 else 'warning' if latest_sys.disk_percent < 95 else 'critical',
                'value': latest_sys.disk_percent,
                'threshold': 85
            },
            'redis_connection': {
                'status': 'healthy' if latest_sys.redis_connected_clients >= 0 else 'critical',
                'value': latest_sys.redis_connected_clients,
                'threshold': 0
            },
            'api_response_time': {
                'status': 'healthy' if latest_app.avg_response_time_ms < 500 else 'warning' if latest_app.avg_response_time_ms < 1000 else 'critical',
                'value': latest_app.avg_response_time_ms,
                'threshold': 500
            },
            'error_rate': {
                'status': 'healthy' if latest_app.error_rate_percent < 1 else 'warning' if latest_app.error_rate_percent < 5 else 'critical',
                'value': latest_app.error_rate_percent,
                'threshold': 1
            },
            'cache_hit_rate': {
                'status': 'healthy' if latest_app.cache_hit_rate > 80 else 'warning' if latest_app.cache_hit_rate > 60 else 'critical',
                'value': latest_app.cache_hit_rate,
                'threshold': 80
            }
        }
        
        # Determine overall status
        critical_count = sum(1 for check in checks.values() if check['status'] == 'critical')
        warning_count = sum(1 for check in checks.values() if check['status'] == 'warning')
        
        if critical_count > 0:
            overall_status = 'critical'
            message = f'{critical_count} critical issues detected'
        elif warning_count > 0:
            overall_status = 'warning'
            message = f'{warning_count} warnings detected'
        else:
            overall_status = 'healthy'
            message = 'All systems operational'
        
        return {
            'status': overall_status,
            'message': message,
            'checks': checks,
            'last_updated': latest_sys.timestamp
        }


# Flask dashboard application
app = Flask(__name__)
monitor = HealthMonitor()


@app.route('/')
def dashboard():
    """Main dashboard page"""
    return render_template('dashboard.html')


@app.route('/api/health')
def health_status():
    """Get current health status"""
    return jsonify(monitor.get_health_status())


@app.route('/api/metrics/system')
def system_metrics():
    """Get system metrics history"""
    # Return last 60 data points (1 hour)
    recent_metrics = monitor.metrics_history[-60:] if len(monitor.metrics_history) > 60 else monitor.metrics_history
    return jsonify([asdict(m) for m in recent_metrics])


@app.route('/api/metrics/application')
def application_metrics():
    """Get application metrics history"""
    # Return last 60 data points (1 hour)
    recent_metrics = monitor.app_metrics_history[-60:] if len(monitor.app_metrics_history) > 60 else monitor.app_metrics_history
    return jsonify([asdict(m) for m in recent_metrics])


@app.route('/api/metrics/current')
def current_metrics():
    """Get current metrics snapshot"""
    if monitor.metrics_history and monitor.app_metrics_history:
        return jsonify({
            'system': asdict(monitor.metrics_history[-1]),
            'application': asdict(monitor.app_metrics_history[-1])
        })
    else:
        return jsonify({'error': 'No metrics available'}), 503


if __name__ == '__main__':
    # Start monitoring
    monitor.start_monitoring()
    
    try:
        # Run Flask app
        app.run(host='0.0.0.0', port=8080, debug=False)
    except KeyboardInterrupt:
        print("Shutting down monitoring...")
        monitor.stop_monitoring()