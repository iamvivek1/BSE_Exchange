#!/usr/bin/env python3
"""
Demo script showing BatchDataFetcher integration with Redis cache.

This example demonstrates:
1. Setting up BatchDataFetcher with symbol prioritization
2. Integrating with Redis cache for data storage
3. Handling batch updates and error scenarios
4. Performance monitoring and statistics
"""

import time
import logging
from datetime import datetime
from services.batch_data_fetcher import BatchDataFetcher, SymbolPriority
from cache.redis_manager import RedisManager
from config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def cache_update_callback(quotes_data):
    """
    Callback function to update Redis cache when new data is fetched.
    
    Args:
        quotes_data: Dictionary of symbol -> StockQuote
    """
    try:
        redis_config = Config.get_redis_config()
        cache_manager = RedisManager(**redis_config)
        
        for symbol, quote in quotes_data.items():
            success = cache_manager.set_stock_data(symbol, quote, ttl=300)  # 5 minute TTL
            if success:
                logger.info(f"Cached updated data for {symbol}: {quote.current_price}")
            else:
                logger.warning(f"Failed to cache data for {symbol}")
                
    except Exception as e:
        logger.error(f"Error in cache update callback: {e}")


def main():
    """Main demo function."""
    logger.info("Starting BatchDataFetcher Demo")
    
    try:
        # Initialize BatchDataFetcher
        fetcher = BatchDataFetcher(
            max_batch_size=10,
            max_retries=3,
            base_retry_delay=1.0,
            max_retry_delay=30.0
        )
        
        # Add cache update callback
        fetcher.add_update_callback(cache_update_callback)
        
        # Add some popular BSE stocks with different priorities
        popular_stocks = [
            ("500325", SymbolPriority.HIGH),    # Reliance Industries
            ("500209", SymbolPriority.HIGH),    # Infosys
            ("532540", SymbolPriority.MEDIUM),  # TCS
            ("500180", SymbolPriority.MEDIUM),  # HDFC Bank
            ("532215", SymbolPriority.LOW),     # Axis Bank
            ("500034", SymbolPriority.LOW),     # Bajaj Finance
        ]
        
        logger.info("Adding stocks to watch list...")
        for symbol, priority in popular_stocks:
            success = fetcher.add_symbol_to_watch(symbol, priority)
            if success:
                logger.info(f"Added {symbol} with priority {priority.name}")
        
        # Demonstrate manual batch fetch
        logger.info("\n=== Manual Batch Fetch Demo ===")
        symbols_to_fetch = ["500325", "500209", "532540"]
        
        logger.info(f"Fetching batch: {symbols_to_fetch}")
        result = fetcher.fetch_batch_quotes(symbols_to_fetch)
        
        logger.info(f"Batch fetch completed:")
        logger.info(f"  Successful: {len(result.successful_quotes)}")
        logger.info(f"  Failed: {len(result.failed_symbols)}")
        logger.info(f"  Duration: {result.batch_duration:.2f}s")
        
        if result.successful_quotes:
            logger.info("  Successful quotes:")
            for symbol, quote in result.successful_quotes.items():
                logger.info(f"    {symbol}: {quote.company_name} - ₹{quote.current_price} ({quote.change:+.2f})")
        
        if result.failed_symbols:
            logger.info("  Failed symbols:")
            for symbol, error in result.failed_symbols.items():
                logger.info(f"    {symbol}: {error}")
        
        # Demonstrate priority-based updates
        logger.info("\n=== Priority-Based Update Demo ===")
        
        # Simulate some time passing
        time.sleep(1)
        
        # Check which symbols need updates
        symbols_needing_update = fetcher.get_symbols_needing_update()
        logger.info(f"Symbols needing update: {symbols_needing_update}")
        
        if symbols_needing_update:
            logger.info("Fetching updates for priority symbols...")
            update_result = fetcher.fetch_batch_quotes(symbols_needing_update)
            logger.info(f"Priority update completed: {len(update_result.successful_quotes)} successful")
        
        # Show performance statistics
        logger.info("\n=== Performance Statistics ===")
        perf_stats = fetcher.get_performance_stats()
        for key, value in perf_stats.items():
            logger.info(f"  {key}: {value}")
        
        # Show individual symbol statistics
        logger.info("\n=== Symbol Statistics ===")
        symbol_stats = fetcher.get_symbol_stats()
        for symbol, stats in symbol_stats.items():
            logger.info(f"  {symbol}:")
            for stat_key, stat_value in stats.items():
                logger.info(f"    {stat_key}: {stat_value}")
        
        # Demonstrate error handling
        logger.info("\n=== Error Handling Demo ===")
        
        # Try to fetch an invalid symbol
        logger.info("Attempting to fetch invalid symbol...")
        error_result = fetcher.fetch_batch_quotes(["INVALID_SYMBOL"])
        
        if error_result.failed_symbols:
            logger.info("Error handling working correctly:")
            for symbol, error in error_result.failed_symbols.items():
                logger.info(f"  {symbol}: {error}")
        
        # Demonstrate cache integration
        logger.info("\n=== Cache Integration Demo ===")
        
        try:
            redis_config = Config.get_redis_config()
            cache_manager = RedisManager(**redis_config)
            
            # Check if our fetched data is in cache
            for symbol in ["500325", "500209"]:
                cached_quote = cache_manager.get_stock_data(symbol)
                if cached_quote:
                    logger.info(f"Found {symbol} in cache: ₹{cached_quote.current_price}")
                    logger.info(f"  Cache TTL: {cache_manager.get_ttl(symbol)}s remaining")
                else:
                    logger.info(f"No cached data found for {symbol}")
        
        except Exception as e:
            logger.warning(f"Cache integration demo failed (Redis not available?): {e}")
        
        # Demonstrate periodic updates (run for a short time)
        logger.info("\n=== Periodic Updates Demo ===")
        logger.info("Starting periodic updates for 10 seconds...")
        
        # Start periodic updates
        update_thread = fetcher.schedule_periodic_updates(interval=3)
        
        # Let it run for a bit
        time.sleep(10)
        
        logger.info("Periodic updates demo completed")
        
        # Final statistics
        logger.info("\n=== Final Statistics ===")
        final_stats = fetcher.get_performance_stats()
        logger.info(f"Total requests: {final_stats['total_requests']}")
        logger.info(f"Success rate: {final_stats['success_rate_percent']}%")
        logger.info(f"Watched symbols: {final_stats['watched_symbols_count']}")
        
    except KeyboardInterrupt:
        logger.info("Demo interrupted by user")
    except Exception as e:
        logger.error(f"Demo failed with error: {e}")
        raise
    finally:
        logger.info("BatchDataFetcher Demo completed")


if __name__ == "__main__":
    main()