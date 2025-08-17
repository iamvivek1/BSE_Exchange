"""
Cache Integration Service

This service integrates the BatchDataFetcher with CacheManager and WebSocketManager
to provide real-time cache updates and broadcasting functionality.
"""

import logging
import threading
import time
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta

from cache.redis_manager import RedisManager
from services.batch_data_fetcher import BatchDataFetcher, SymbolPriority
from services.websocket_manager import WebSocketManager
from models.stock_quote import StockQuote


class CacheIntegrationService:
    """
    Integrates cache, batch fetcher, and WebSocket manager for real-time updates.
    
    Features:
    - Automatic cache updates from batch fetcher
    - Real-time broadcasting via WebSocket
    - Cache warming for essential stocks
    - Intelligent cache invalidation and refresh
    """
    
    def __init__(self, cache_manager: RedisManager, batch_fetcher: BatchDataFetcher, 
                 websocket_manager: Optional[WebSocketManager] = None):
        """
        Initialize the integration service.
        
        Args:
            cache_manager: Redis cache manager instance
            batch_fetcher: Batch data fetcher instance
            websocket_manager: WebSocket manager instance (optional)
        """
        self.cache_manager = cache_manager
        self.batch_fetcher = batch_fetcher
        self.websocket_manager = websocket_manager
        
        self.logger = logging.getLogger(__name__)
        
        # Essential stocks for cache warming
        self.essential_stocks: Set[str] = set()
        
        # Integration state
        self.is_running = False
        self.subscription_thread: Optional[threading.Thread] = None
        
        # Performance tracking
        self.cache_hits = 0
        self.cache_misses = 0
        self.updates_processed = 0
        self.broadcasts_sent = 0
        
        # Setup integration
        self._setup_integration()
        
        self.logger.info("CacheIntegrationService initialized")
    
    def _setup_integration(self):
        """Setup integration between components."""
        # Add callback to batch fetcher for cache updates
        self.batch_fetcher.add_update_callback(self._handle_batch_updates)
        
        # Subscribe to Redis pub/sub for real-time updates
        if self.websocket_manager:
            self.subscription_thread = self.cache_manager.subscribe_to_updates(
                self._handle_cache_updates
            )
        
        self.logger.debug("Integration setup completed")
    
    def _handle_batch_updates(self, stock_quotes: Dict[str, StockQuote]):
        """
        Handle updates from batch fetcher by updating cache and broadcasting.
        
        Args:
            stock_quotes: Dictionary of symbol -> StockQuote from batch fetcher
        """
        self.logger.debug(f"Processing batch updates for {len(stock_quotes)} symbols")
        
        for symbol, stock_quote in stock_quotes.items():
            try:
                # Update cache and publish to Redis pub/sub
                success = self.cache_manager.refresh_stock_data(
                    symbol, stock_quote, publish=True
                )
                
                if success:
                    self.updates_processed += 1
                    self.logger.debug(f"Updated cache for {symbol}")
                else:
                    self.logger.warning(f"Failed to update cache for {symbol}")
                    
            except Exception as e:
                self.logger.error(f"Error processing update for {symbol}: {e}")
    
    def _handle_cache_updates(self, symbol: str, stock_quote: StockQuote):
        """
        Handle cache updates by broadcasting to WebSocket clients.
        
        Args:
            symbol: Stock symbol that was updated
            stock_quote: Updated stock quote data
        """
        if not self.websocket_manager:
            return
        
        try:
            # Convert to WebSocket message format
            data = stock_quote.to_dict()
            
            # Broadcast to subscribed clients
            self.websocket_manager.broadcast_stock_update(symbol, data)
            self.broadcasts_sent += 1
            
            self.logger.debug(f"Broadcasted update for {symbol}")
            
        except Exception as e:
            self.logger.error(f"Error broadcasting update for {symbol}: {e}")
    
    def add_essential_stock(self, symbol: str, priority: SymbolPriority = SymbolPriority.HIGH):
        """
        Add a stock to the essential stocks list for cache warming.
        
        Args:
            symbol: Stock symbol to add
            priority: Priority level for the stock
        """
        self.essential_stocks.add(symbol)
        
        # Add to batch fetcher with high priority
        self.batch_fetcher.add_symbol_to_watch(symbol, priority)
        
        self.logger.info(f"Added essential stock {symbol} with priority {priority.name}")
    
    def remove_essential_stock(self, symbol: str):
        """
        Remove a stock from the essential stocks list.
        
        Args:
            symbol: Stock symbol to remove
        """
        self.essential_stocks.discard(symbol)
        self.batch_fetcher.remove_symbol_from_watch(symbol)
        
        self.logger.info(f"Removed essential stock {symbol}")
    
    def warm_cache_for_essentials(self) -> Dict[str, bool]:
        """
        Warm the cache with current data for essential stocks.
        
        Returns:
            Dictionary of symbol -> success status
        """
        if not self.essential_stocks:
            self.logger.info("No essential stocks defined for cache warming")
            return {}
        
        self.logger.info(f"Warming cache for {len(self.essential_stocks)} essential stocks")
        
        # Fetch current data for essential stocks
        essential_list = list(self.essential_stocks)
        batch_result = self.batch_fetcher.fetch_batch_quotes(essential_list)
        
        # Warm cache with successful fetches
        if batch_result.successful_quotes:
            warm_results = self.cache_manager.warm_cache(
                batch_result.successful_quotes,
                ttl=600  # 10 minutes for essential stocks
            )
            
            self.logger.info(f"Cache warming completed: {sum(warm_results.values())}/{len(warm_results)} successful")
            return warm_results
        else:
            self.logger.warning("No successful quotes fetched for cache warming")
            return {}
    
    def get_stock_data(self, symbol: str, fetch_if_missing: bool = True) -> Optional[StockQuote]:
        """
        Get stock data from cache with optional fallback to live fetch.
        
        Args:
            symbol: Stock symbol to retrieve
            fetch_if_missing: Whether to fetch from API if not in cache
            
        Returns:
            StockQuote object if found, None otherwise
        """
        # Try cache first
        stock_quote = self.cache_manager.get_stock_data(symbol)
        
        if stock_quote:
            self.cache_hits += 1
            self.logger.debug(f"Cache hit for {symbol}")
            return stock_quote
        
        self.cache_misses += 1
        self.logger.debug(f"Cache miss for {symbol}")
        
        # Fetch from API if requested and not in cache
        if fetch_if_missing:
            self.logger.debug(f"Fetching {symbol} from API due to cache miss")
            
            batch_result = self.batch_fetcher.fetch_batch_quotes([symbol])
            
            if symbol in batch_result.successful_quotes:
                stock_quote = batch_result.successful_quotes[symbol]
                
                # Cache the result
                self.cache_manager.refresh_stock_data(symbol, stock_quote, publish=True)
                
                return stock_quote
        
        return None
    
    def invalidate_and_refresh(self, symbols: List[str]) -> Dict[str, bool]:
        """
        Invalidate cache for symbols and refresh with new data.
        
        Args:
            symbols: List of symbols to invalidate and refresh
            
        Returns:
            Dictionary of symbol -> success status
        """
        results = {}
        
        # Invalidate cache entries
        for symbol in symbols:
            self.cache_manager.invalidate_stock_data(symbol)
        
        # Fetch fresh data
        batch_result = self.batch_fetcher.fetch_batch_quotes(symbols)
        
        # Update cache with fresh data
        for symbol in symbols:
            if symbol in batch_result.successful_quotes:
                stock_quote = batch_result.successful_quotes[symbol]
                success = self.cache_manager.refresh_stock_data(symbol, stock_quote, publish=True)
                results[symbol] = success
            else:
                results[symbol] = False
        
        self.logger.info(f"Invalidated and refreshed {len(symbols)} symbols: "
                        f"{sum(results.values())} successful")
        
        return results
    
    def start_periodic_cache_warming(self, interval: int = 300):
        """
        Start periodic cache warming for essential stocks.
        
        Args:
            interval: Warming interval in seconds (default: 5 minutes)
        """
        def warming_loop():
            self.logger.info(f"Starting periodic cache warming with {interval}s interval")
            
            while self.is_running:
                try:
                    if self.essential_stocks:
                        self.warm_cache_for_essentials()
                    
                    time.sleep(interval)
                    
                except Exception as e:
                    self.logger.error(f"Error in cache warming loop: {e}")
                    time.sleep(interval)
        
        if not self.is_running:
            self.is_running = True
            warming_thread = threading.Thread(target=warming_loop, daemon=True)
            warming_thread.start()
            
            self.logger.info("Periodic cache warming started")
            return warming_thread
        else:
            self.logger.warning("Periodic cache warming already running")
            return None
    
    def stop(self):
        """Stop the integration service."""
        self.is_running = False
        
        if self.subscription_thread and self.subscription_thread.is_alive():
            # Note: Redis pubsub threads are daemon threads and will stop automatically
            pass
        
        self.logger.info("CacheIntegrationService stopped")
    
    def get_performance_stats(self) -> Dict[str, any]:
        """
        Get performance statistics for the integration service.
        
        Returns:
            Dictionary with performance metrics
        """
        cache_hit_rate = 0.0
        total_cache_requests = self.cache_hits + self.cache_misses
        
        if total_cache_requests > 0:
            cache_hit_rate = (self.cache_hits / total_cache_requests) * 100
        
        return {
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'cache_hit_rate_percent': round(cache_hit_rate, 2),
            'updates_processed': self.updates_processed,
            'broadcasts_sent': self.broadcasts_sent,
            'essential_stocks_count': len(self.essential_stocks),
            'essential_stocks': list(self.essential_stocks),
            'is_running': self.is_running
        }
    
    def get_cache_status(self) -> Dict[str, any]:
        """
        Get current cache status information.
        
        Returns:
            Dictionary with cache status
        """
        cached_symbols = self.cache_manager.get_cached_symbols()
        cache_info = self.cache_manager.get_cache_info()
        
        return {
            'cached_symbols_count': len(cached_symbols),
            'cached_symbols': cached_symbols,
            'redis_info': cache_info
        }