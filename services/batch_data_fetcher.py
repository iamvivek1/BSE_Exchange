import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Callable
from dataclasses import dataclass, field
from enum import Enum
import random
from bsedata.bse import BSE
from models.stock_quote import StockQuote
from services.monitoring_service import MonitoringService
from services.error_handling_service import ErrorHandlingService, FallbackStrategy


class SymbolPriority(Enum):
    """Priority levels for stock symbols."""
    HIGH = 1    # Update every 5 seconds
    MEDIUM = 2  # Update every 15 seconds  
    LOW = 3     # Update every 30 seconds


@dataclass
class SymbolConfig:
    """Configuration for a watched symbol."""
    symbol: str
    priority: SymbolPriority = SymbolPriority.MEDIUM
    last_updated: Optional[datetime] = None
    update_count: int = 0
    error_count: int = 0
    last_error: Optional[str] = None


@dataclass
class BatchResult:
    """Result of a batch fetch operation."""
    successful_quotes: Dict[str, StockQuote] = field(default_factory=dict)
    failed_symbols: Dict[str, str] = field(default_factory=dict)  # symbol -> error message
    fetch_time: datetime = field(default_factory=datetime.now)
    batch_duration: float = 0.0


class BatchDataFetcher:
    """
    Efficiently fetches multiple stock quotes from BSE API in batches.
    
    Features:
    - Batch processing of up to 20 symbols per API call
    - Symbol prioritization with different update frequencies
    - Exponential backoff for failed requests
    - Automatic retry logic with circuit breaker pattern
    """
    
    def __init__(self, max_batch_size: int = 20, max_retries: int = 3, 
                 base_retry_delay: float = 1.0, max_retry_delay: float = 60.0,
                 monitoring_service: Optional[MonitoringService] = None,
                 error_handler: Optional[ErrorHandlingService] = None):
        """
        Initialize BatchDataFetcher.
        
        Args:
            max_batch_size: Maximum symbols per batch (BSE API limit)
            max_retries: Maximum retry attempts for failed requests
            base_retry_delay: Base delay for exponential backoff (seconds)
            max_retry_delay: Maximum retry delay (seconds)
            monitoring_service: Optional monitoring service for metrics
            error_handler: Optional error handler for graceful degradation
        """
        self.max_batch_size = max_batch_size
        self.max_retries = max_retries
        self.base_retry_delay = base_retry_delay
        self.max_retry_delay = max_retry_delay
        
        self.logger = logging.getLogger(__name__)
        self.bse_client = BSE(update_codes=True)
        
        # Monitoring and error handling
        self.monitoring_service = monitoring_service
        self.error_handler = error_handler
        
        # Symbol management
        self.watched_symbols: Dict[str, SymbolConfig] = {}
        self.update_callbacks: List[Callable[[Dict[str, StockQuote]], None]] = []
        
        # Circuit breaker state (legacy - prefer monitoring_service circuit breaker)
        self.circuit_breaker_failures = 0
        self.circuit_breaker_threshold = 5
        self.circuit_breaker_reset_time = None
        self.circuit_breaker_timeout = 300  # 5 minutes
        
        # Performance tracking
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.last_batch_time = None
        
        self.logger.info("BatchDataFetcher initialized")
    
    def add_symbol_to_watch(self, symbol: str, priority: SymbolPriority = SymbolPriority.MEDIUM) -> bool:
        """
        Add a symbol to the watch list.
        
        Args:
            symbol: Stock symbol to watch
            priority: Priority level for updates
            
        Returns:
            True if added successfully, False if already exists
        """
        if symbol in self.watched_symbols:
            self.logger.debug(f"Symbol {symbol} already being watched")
            return False
        
        self.watched_symbols[symbol] = SymbolConfig(symbol=symbol, priority=priority)
        self.logger.info(f"Added symbol {symbol} to watch list with priority {priority.name}")
        return True
    
    def remove_symbol_from_watch(self, symbol: str) -> bool:
        """
        Remove a symbol from the watch list.
        
        Args:
            symbol: Stock symbol to remove
            
        Returns:
            True if removed successfully, False if not found
        """
        if symbol not in self.watched_symbols:
            self.logger.debug(f"Symbol {symbol} not in watch list")
            return False
        
        del self.watched_symbols[symbol]
        self.logger.info(f"Removed symbol {symbol} from watch list")
        return True
    
    def update_symbol_priority(self, symbol: str, priority: SymbolPriority) -> bool:
        """
        Update the priority of a watched symbol.
        
        Args:
            symbol: Stock symbol
            priority: New priority level
            
        Returns:
            True if updated successfully, False if symbol not found
        """
        if symbol not in self.watched_symbols:
            self.logger.warning(f"Cannot update priority for unwatched symbol {symbol}")
            return False
        
        old_priority = self.watched_symbols[symbol].priority
        self.watched_symbols[symbol].priority = priority
        self.logger.info(f"Updated symbol {symbol} priority from {old_priority.name} to {priority.name}")
        return True
    
    def add_update_callback(self, callback: Callable[[Dict[str, StockQuote]], None]):
        """
        Add a callback function to be called when new data is fetched.
        
        Args:
            callback: Function that accepts a dict of symbol -> StockQuote
        """
        self.update_callbacks.append(callback)
        self.logger.debug(f"Added update callback: {callback.__name__}")
    
    def _is_circuit_breaker_open(self) -> bool:
        """Check if circuit breaker is currently open."""
        if self.circuit_breaker_failures < self.circuit_breaker_threshold:
            return False
        
        if self.circuit_breaker_reset_time is None:
            self.circuit_breaker_reset_time = datetime.now() + timedelta(seconds=self.circuit_breaker_timeout)
            return True
        
        if datetime.now() >= self.circuit_breaker_reset_time:
            # Reset circuit breaker
            self.circuit_breaker_failures = 0
            self.circuit_breaker_reset_time = None
            self.logger.info("Circuit breaker reset")
            return False
        
        return True
    
    def _calculate_retry_delay(self, attempt: int) -> float:
        """
        Calculate exponential backoff delay with jitter.
        
        Args:
            attempt: Current retry attempt (0-based)
            
        Returns:
            Delay in seconds
        """
        # Exponential backoff: base_delay * (2 ^ attempt)
        delay = self.base_retry_delay * (2 ** attempt)
        
        # Add jitter (±25% randomization)
        jitter = delay * 0.25 * (2 * random.random() - 1)
        delay += jitter
        
        # Cap at maximum delay
        return min(delay, self.max_retry_delay)
    
    def _fetch_single_quote(self, symbol: str) -> Optional[StockQuote]:
        """
        Fetch a single stock quote from BSE API.
        
        Args:
            symbol: Stock symbol to fetch
            
        Returns:
            StockQuote object if successful, None otherwise
        """
        start_time = time.time()
        
        try:
            # Use circuit breaker if available
            if self.monitoring_service:
                circuit_breaker = self.monitoring_service.get_circuit_breaker("bse_api")
                if circuit_breaker:
                    quote_data = circuit_breaker.call(self.bse_client.getQuote, symbol)
                else:
                    quote_data = self.bse_client.getQuote(symbol)
            else:
                quote_data = self.bse_client.getQuote(symbol)
            
            if not quote_data:
                self.logger.warning(f"No data returned for symbol {symbol}")
                return None
            
            # Convert BSE API response to StockQuote
            stock_quote = StockQuote(
                symbol=symbol,
                company_name=quote_data.get("companyName", "Unknown"),
                current_price=float(quote_data.get("currentValue", 0)),
                change=float(quote_data.get("change", 0)),
                percent_change=float(quote_data.get("pChange", 0)),
                volume=int(quote_data.get("totalTradedQuantity", 0)),
                timestamp=datetime.now(),
                high=quote_data.get("dayHigh"),
                low=quote_data.get("dayLow"),
                bid_price=quote_data.get("buy"),
                ask_price=quote_data.get("sell")
            )
            
            # Record successful API call metrics
            if self.monitoring_service:
                duration = time.time() - start_time
                self.monitoring_service.metrics.record_timing("bse_api_response_time", duration, {"symbol": symbol})
                self.monitoring_service.metrics.record_counter("bse_api_requests_success", 1, {"symbol": symbol})
            
            # Record success in error handler
            if self.error_handler:
                self.error_handler.record_success("bse_api", stock_quote.to_dict())
            
            return stock_quote
            
        except Exception as e:
            duration = time.time() - start_time
            
            # Record error metrics
            if self.monitoring_service:
                self.monitoring_service.metrics.record_timing("bse_api_response_time", duration, {"symbol": symbol, "status": "error"})
                self.monitoring_service.metrics.record_counter("bse_api_requests_error", 1, {"symbol": symbol})
            
            # Record error in error handler
            if self.error_handler:
                self.error_handler.record_error("bse_api", f"Failed to fetch {symbol}: {e}")
            
            self.logger.error(f"Failed to fetch quote for {symbol}: {e}")
            return None
    
    def fetch_batch_quotes(self, symbols: List[str]) -> BatchResult:
        """
        Fetch quotes for multiple symbols with retry logic.
        
        Args:
            symbols: List of stock symbols to fetch
            
        Returns:
            BatchResult containing successful and failed fetches
        """
        start_time = time.time()
        result = BatchResult()
        
        if self._is_circuit_breaker_open():
            error_msg = "Circuit breaker is open, skipping batch fetch"
            self.logger.warning(error_msg)
            result.failed_symbols = {symbol: error_msg for symbol in symbols}
            return result
        
        # Limit batch size
        if len(symbols) > self.max_batch_size:
            self.logger.warning(f"Batch size {len(symbols)} exceeds limit {self.max_batch_size}, truncating")
            symbols = symbols[:self.max_batch_size]
        
        self.logger.debug(f"Fetching batch of {len(symbols)} symbols: {symbols}")
        
        for symbol in symbols:
            success = False
            last_error = None
            
            # Retry logic with exponential backoff
            for attempt in range(self.max_retries + 1):
                try:
                    quote = self._fetch_single_quote(symbol)
                    
                    if quote is not None:
                        result.successful_quotes[symbol] = quote
                        success = True
                        
                        # Update symbol config
                        if symbol in self.watched_symbols:
                            config = self.watched_symbols[symbol]
                            config.last_updated = datetime.now()
                            config.update_count += 1
                            config.error_count = 0  # Reset error count on success
                            config.last_error = None
                        
                        break
                    else:
                        last_error = "No data returned from API"
                        
                except Exception as e:
                    last_error = str(e)
                    self.logger.warning(f"Attempt {attempt + 1} failed for {symbol}: {e}")
                
                # Wait before retry (except on last attempt)
                if attempt < self.max_retries:
                    delay = self._calculate_retry_delay(attempt)
                    self.logger.debug(f"Retrying {symbol} in {delay:.2f} seconds")
                    time.sleep(delay)
            
            if not success:
                result.failed_symbols[symbol] = last_error or "Unknown error"
                self.circuit_breaker_failures += 1
                
                # Update symbol config for failure
                if symbol in self.watched_symbols:
                    config = self.watched_symbols[symbol]
                    config.error_count += 1
                    config.last_error = last_error
        
        # Update performance metrics
        self.total_requests += 1
        if result.successful_quotes:
            self.successful_requests += 1
        if result.failed_symbols:
            self.failed_requests += 1
        
        result.batch_duration = time.time() - start_time
        self.last_batch_time = result.fetch_time
        
        self.logger.info(f"Batch fetch completed: {len(result.successful_quotes)} successful, "
                        f"{len(result.failed_symbols)} failed, duration: {result.batch_duration:.2f}s")
        
        # Notify callbacks
        if result.successful_quotes and self.update_callbacks:
            for callback in self.update_callbacks:
                try:
                    callback(result.successful_quotes)
                except Exception as e:
                    self.logger.error(f"Error in update callback {callback.__name__}: {e}")
        
        return result
    
    def get_symbols_needing_update(self) -> List[str]:
        """
        Get list of symbols that need updating based on their priority and last update time.
        
        Returns:
            List of symbols that should be updated
        """
        now = datetime.now()
        symbols_to_update = []
        
        # Priority-based update intervals
        update_intervals = {
            SymbolPriority.HIGH: 5,    # 5 seconds
            SymbolPriority.MEDIUM: 15, # 15 seconds
            SymbolPriority.LOW: 30     # 30 seconds
        }
        
        for symbol, config in self.watched_symbols.items():
            interval = update_intervals[config.priority]
            
            # If never updated or interval has passed
            if (config.last_updated is None or 
                (now - config.last_updated).total_seconds() >= interval):
                symbols_to_update.append(symbol)
        
        return symbols_to_update
    
    def schedule_periodic_updates(self, interval: int = 5):
        """
        Schedule periodic updates for watched symbols.
        
        Args:
            interval: Check interval in seconds
        """
        self.logger.info(f"Starting periodic updates with {interval}s interval")
        
        def update_loop():
            while True:
                try:
                    symbols_to_update = self.get_symbols_needing_update()
                    
                    if symbols_to_update:
                        self.logger.debug(f"Updating {len(symbols_to_update)} symbols")
                        self.fetch_batch_quotes(symbols_to_update)
                    
                    time.sleep(interval)
                    
                except KeyboardInterrupt:
                    self.logger.info("Periodic updates stopped by user")
                    break
                except Exception as e:
                    self.logger.error(f"Error in periodic update loop: {e}")
                    time.sleep(interval)  # Continue after error
        
        # Run in separate thread to avoid blocking
        import threading
        update_thread = threading.Thread(target=update_loop, daemon=True)
        update_thread.start()
        
        return update_thread
    
    def get_performance_stats(self) -> Dict[str, any]:
        """
        Get performance statistics for the batch fetcher.
        
        Returns:
            Dictionary with performance metrics
        """
        success_rate = 0.0
        if self.total_requests > 0:
            success_rate = (self.successful_requests / self.total_requests) * 100
        
        return {
            'total_requests': self.total_requests,
            'successful_requests': self.successful_requests,
            'failed_requests': self.failed_requests,
            'success_rate_percent': round(success_rate, 2),
            'watched_symbols_count': len(self.watched_symbols),
            'circuit_breaker_failures': self.circuit_breaker_failures,
            'circuit_breaker_open': self._is_circuit_breaker_open(),
            'last_batch_time': self.last_batch_time.isoformat() if self.last_batch_time else None
        }
    
    def get_symbol_stats(self) -> Dict[str, Dict[str, any]]:
        """
        Get statistics for individual symbols.
        
        Returns:
            Dictionary mapping symbol to its statistics
        """
        stats = {}
        
        for symbol, config in self.watched_symbols.items():
            stats[symbol] = {
                'priority': config.priority.name,
                'update_count': config.update_count,
                'error_count': config.error_count,
                'last_updated': config.last_updated.isoformat() if config.last_updated else None,
                'last_error': config.last_error
            }
        
        return stats