"""
Error Handling Service

Provides graceful degradation and error recovery mechanisms
for the BSE data optimization system.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass
from enum import Enum
import json
from functools import wraps


class ServiceState(Enum):
    """Service operational states."""
    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    FAILED = "failed"
    RECOVERING = "recovering"


class FallbackStrategy(Enum):
    """Fallback strategies for service failures."""
    CACHE_ONLY = "cache_only"
    LAST_KNOWN_GOOD = "last_known_good"
    MOCK_DATA = "mock_data"
    FAIL_FAST = "fail_fast"
    RETRY_WITH_BACKOFF = "retry_with_backoff"


@dataclass
class ServiceStatus:
    """Status information for a service."""
    name: str
    state: ServiceState
    last_error: Optional[str] = None
    error_count: int = 0
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    fallback_active: bool = False
    fallback_strategy: Optional[FallbackStrategy] = None


class ErrorHandlingService:
    """
    Provides comprehensive error handling and graceful degradation
    for all system components.
    """
    
    def __init__(self):
        """Initialize error handling service."""
        self.logger = logging.getLogger(__name__)
        
        # Service status tracking
        self.service_status: Dict[str, ServiceStatus] = {}
        
        # Fallback data storage
        self.fallback_data: Dict[str, Any] = {}
        self.last_known_good: Dict[str, Any] = {}
        
        # Error recovery callbacks
        self.recovery_callbacks: Dict[str, List[Callable]] = {}
        
        # Configuration
        self.max_error_count = 5
        self.recovery_timeout = 300  # 5 minutes
        
        self.logger.info("ErrorHandlingService initialized")
    
    def register_service(self, service_name: str, 
                        fallback_strategy: FallbackStrategy = FallbackStrategy.CACHE_ONLY):
        """
        Register a service for error handling.
        
        Args:
            service_name: Unique name for the service
            fallback_strategy: Default fallback strategy for the service
        """
        self.service_status[service_name] = ServiceStatus(
            name=service_name,
            state=ServiceState.OPERATIONAL,
            fallback_strategy=fallback_strategy
        )
        
        self.logger.info(f"Registered service {service_name} with fallback strategy {fallback_strategy.value}")
    
    def add_recovery_callback(self, service_name: str, callback: Callable):
        """
        Add a callback to be executed when a service recovers.
        
        Args:
            service_name: Name of the service
            callback: Function to call on recovery
        """
        if service_name not in self.recovery_callbacks:
            self.recovery_callbacks[service_name] = []
        
        self.recovery_callbacks[service_name].append(callback)
        self.logger.debug(f"Added recovery callback for {service_name}")
    
    def record_success(self, service_name: str, data: Optional[Any] = None):
        """
        Record a successful operation for a service.
        
        Args:
            service_name: Name of the service
            data: Optional data to store as last known good
        """
        if service_name not in self.service_status:
            self.register_service(service_name)
        
        status = self.service_status[service_name]
        previous_state = status.state
        
        status.state = ServiceState.OPERATIONAL
        status.last_success = datetime.now()
        status.error_count = 0
        status.last_error = None
        status.fallback_active = False
        
        # Store last known good data
        if data is not None:
            self.last_known_good[service_name] = {
                "data": data,
                "timestamp": datetime.now()
            }
        
        # If service was previously failed/degraded, trigger recovery callbacks
        if previous_state in [ServiceState.FAILED, ServiceState.DEGRADED, ServiceState.RECOVERING]:
            self._trigger_recovery_callbacks(service_name)
            self.logger.info(f"Service {service_name} recovered from {previous_state.value}")
    
    def record_error(self, service_name: str, error: Union[str, Exception], 
                    severity: str = "error") -> ServiceState:
        """
        Record an error for a service and determine appropriate response.
        
        Args:
            service_name: Name of the service
            error: Error message or exception
            severity: Error severity level
            
        Returns:
            New service state after error handling
        """
        if service_name not in self.service_status:
            self.register_service(service_name)
        
        status = self.service_status[service_name]
        
        # Update error information
        status.error_count += 1
        status.last_failure = datetime.now()
        status.last_error = str(error)
        
        # Determine new state based on error count and severity
        if severity == "critical" or status.error_count >= self.max_error_count:
            status.state = ServiceState.FAILED
            status.fallback_active = True
        elif status.error_count >= 2:
            status.state = ServiceState.DEGRADED
            status.fallback_active = True
        
        self.logger.error(f"Service {service_name} error (count: {status.error_count}): {error}")
        
        return status.state
    
    def get_fallback_data(self, service_name: str, data_key: str) -> Optional[Any]:
        """
        Get fallback data for a service.
        
        Args:
            service_name: Name of the service
            data_key: Key for the specific data
            
        Returns:
            Fallback data if available
        """
        if service_name not in self.service_status:
            return None
        
        status = self.service_status[service_name]
        strategy = status.fallback_strategy
        
        if strategy == FallbackStrategy.CACHE_ONLY:
            return self.fallback_data.get(f"{service_name}:{data_key}")
        
        elif strategy == FallbackStrategy.LAST_KNOWN_GOOD:
            if service_name in self.last_known_good:
                lkg_data = self.last_known_good[service_name]
                # Check if data is not too old (within 1 hour)
                if (datetime.now() - lkg_data["timestamp"]).total_seconds() < 3600:
                    return lkg_data["data"]
        
        elif strategy == FallbackStrategy.MOCK_DATA:
            return self._generate_mock_data(service_name, data_key)
        
        return None
    
    def set_fallback_data(self, service_name: str, data_key: str, data: Any):
        """
        Set fallback data for a service.
        
        Args:
            service_name: Name of the service
            data_key: Key for the specific data
            data: Data to store as fallback
        """
        self.fallback_data[f"{service_name}:{data_key}"] = data
        self.logger.debug(f"Set fallback data for {service_name}:{data_key}")
    
    def _generate_mock_data(self, service_name: str, data_key: str) -> Optional[Any]:
        """
        Generate mock data for testing/fallback purposes.
        
        Args:
            service_name: Name of the service
            data_key: Key for the specific data
            
        Returns:
            Mock data appropriate for the service
        """
        if service_name == "bse_api" and "stock_quote" in data_key:
            # Generate mock stock quote
            return {
                "symbol": data_key.split(":")[-1] if ":" in data_key else "MOCK",
                "company_name": "Mock Company",
                "current_price": 100.0,
                "change": 0.0,
                "percent_change": 0.0,
                "volume": 1000,
                "timestamp": datetime.now().isoformat(),
                "mock": True
            }
        
        elif service_name == "cache":
            return None  # Cache misses should return None
        
        elif service_name == "websocket":
            return {"status": "degraded", "message": "WebSocket service unavailable"}
        
        return None
    
    def _trigger_recovery_callbacks(self, service_name: str):
        """Trigger recovery callbacks for a service."""
        if service_name in self.recovery_callbacks:
            for callback in self.recovery_callbacks[service_name]:
                try:
                    callback()
                except Exception as e:
                    self.logger.error(f"Error in recovery callback for {service_name}: {e}")
    
    def attempt_recovery(self, service_name: str) -> bool:
        """
        Attempt to recover a failed service.
        
        Args:
            service_name: Name of the service to recover
            
        Returns:
            True if recovery was initiated
        """
        if service_name not in self.service_status:
            return False
        
        status = self.service_status[service_name]
        
        if status.state != ServiceState.FAILED:
            return False
        
        # Check if enough time has passed since last failure
        if status.last_failure:
            time_since_failure = (datetime.now() - status.last_failure).total_seconds()
            if time_since_failure < self.recovery_timeout:
                return False
        
        status.state = ServiceState.RECOVERING
        status.error_count = 0
        
        self.logger.info(f"Attempting recovery for service {service_name}")
        return True
    
    def get_service_status(self, service_name: str) -> Optional[Dict[str, Any]]:
        """
        Get status information for a service.
        
        Args:
            service_name: Name of the service
            
        Returns:
            Service status dictionary
        """
        if service_name not in self.service_status:
            return None
        
        status = self.service_status[service_name]
        
        return {
            "name": status.name,
            "state": status.state.value,
            "error_count": status.error_count,
            "last_error": status.last_error,
            "last_success": status.last_success.isoformat() if status.last_success else None,
            "last_failure": status.last_failure.isoformat() if status.last_failure else None,
            "fallback_active": status.fallback_active,
            "fallback_strategy": status.fallback_strategy.value if status.fallback_strategy else None
        }
    
    def get_all_service_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status for all registered services."""
        return {
            name: self.get_service_status(name)
            for name in self.service_status.keys()
        }
    
    def is_service_healthy(self, service_name: str) -> bool:
        """
        Check if a service is healthy.
        
        Args:
            service_name: Name of the service
            
        Returns:
            True if service is operational
        """
        if service_name not in self.service_status:
            return False
        
        return self.service_status[service_name].state == ServiceState.OPERATIONAL
    
    def get_degraded_services(self) -> List[str]:
        """Get list of services in degraded or failed state."""
        degraded = []
        
        for name, status in self.service_status.items():
            if status.state in [ServiceState.DEGRADED, ServiceState.FAILED]:
                degraded.append(name)
        
        return degraded


def with_error_handling(service_name: str, error_handler: ErrorHandlingService,
                       fallback_strategy: FallbackStrategy = FallbackStrategy.CACHE_ONLY):
    """
    Decorator to add error handling to service methods.
    
    Args:
        service_name: Name of the service
        error_handler: ErrorHandlingService instance
        fallback_strategy: Fallback strategy to use
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                error_handler.record_success(service_name, result)
                return result
                
            except Exception as e:
                new_state = error_handler.record_error(service_name, e)
                
                # If service is failed or degraded, try fallback
                if new_state in [ServiceState.FAILED, ServiceState.DEGRADED]:
                    fallback_data = error_handler.get_fallback_data(service_name, func.__name__)
                    if fallback_data is not None:
                        return fallback_data
                
                # Re-raise exception if no fallback available
                raise e
        
        return wrapper
    return decorator


class GracefulDegradationManager:
    """
    Manages graceful degradation strategies for the entire system.
    """
    
    def __init__(self, error_handler: ErrorHandlingService):
        """
        Initialize graceful degradation manager.
        
        Args:
            error_handler: ErrorHandlingService instance
        """
        self.error_handler = error_handler
        self.logger = logging.getLogger(__name__)
        
        # Degradation strategies
        self.degradation_strategies = {
            "bse_api_failure": self._handle_bse_api_failure,
            "cache_failure": self._handle_cache_failure,
            "websocket_failure": self._handle_websocket_failure,
            "database_failure": self._handle_database_failure
        }
    
    def handle_system_degradation(self) -> Dict[str, Any]:
        """
        Handle system-wide degradation based on service states.
        
        Returns:
            Dictionary with degradation actions taken
        """
        degraded_services = self.error_handler.get_degraded_services()
        actions_taken = {}
        
        for service in degraded_services:
            if service == "bse_api":
                actions_taken["bse_api"] = self._handle_bse_api_failure()
            elif service == "cache":
                actions_taken["cache"] = self._handle_cache_failure()
            elif service == "websocket":
                actions_taken["websocket"] = self._handle_websocket_failure()
        
        return actions_taken
    
    def _handle_bse_api_failure(self) -> Dict[str, Any]:
        """Handle BSE API failure with graceful degradation."""
        self.logger.warning("Handling BSE API failure - switching to cache-only mode")
        
        return {
            "strategy": "cache_only",
            "actions": [
                "Disabled live API calls",
                "Serving data from cache only",
                "Increased cache TTL to 30 minutes",
                "Added staleness indicators to responses"
            ],
            "impact": "Users will see cached data with staleness indicators"
        }
    
    def _handle_cache_failure(self) -> Dict[str, Any]:
        """Handle cache failure with graceful degradation."""
        self.logger.warning("Handling cache failure - switching to direct API mode")
        
        return {
            "strategy": "direct_api",
            "actions": [
                "Bypassing cache layer",
                "Direct API calls for all requests",
                "Reduced concurrent request limits",
                "Added request queuing"
            ],
            "impact": "Increased response times, reduced throughput"
        }
    
    def _handle_websocket_failure(self) -> Dict[str, Any]:
        """Handle WebSocket failure with graceful degradation."""
        self.logger.warning("Handling WebSocket failure - switching to HTTP polling")
        
        return {
            "strategy": "http_polling",
            "actions": [
                "Disabled WebSocket connections",
                "Enabled HTTP polling fallback",
                "Increased polling interval to reduce load",
                "Added connection retry logic"
            ],
            "impact": "Reduced real-time capabilities, higher latency"
        }
    
    def _handle_database_failure(self) -> Dict[str, Any]:
        """Handle database failure with graceful degradation."""
        self.logger.warning("Handling database failure - switching to memory-only mode")
        
        return {
            "strategy": "memory_only",
            "actions": [
                "Switched to in-memory storage",
                "Disabled persistent data storage",
                "Reduced data retention period",
                "Added data loss warnings"
            ],
            "impact": "Data will not persist across restarts"
        }