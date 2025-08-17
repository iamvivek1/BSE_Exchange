#!/usr/bin/env python3
"""
Demo script showing Redis cache infrastructure usage.
This script demonstrates the basic cache operations without requiring a running Redis server.
"""

import sys
import os
from datetime import datetime

# Add parent directory to path to import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.stock_quote import StockQuote
from cache.redis_manager import RedisManager
from config import Config


def demo_stock_quote_serialization():
    """Demonstrate StockQuote serialization capabilities."""
    print("=== StockQuote Serialization Demo ===")
    
    # Create a sample stock quote
    quote = StockQuote(
        symbol='500325',
        company_name='Reliance Industries Ltd',
        current_price=2501.50,
        change=1.50,
        percent_change=0.06,
        volume=1000000,
        timestamp=datetime.now(),
        bid_price=2501.00,
        ask_price=2502.00,
        high=2510.00,
        low=2495.00
    )
    
    print(f"Original Quote: {quote.symbol} - {quote.company_name}")
    print(f"Price: ₹{quote.current_price} (Change: {quote.change:+.2f})")
    
    # Test serialization methods
    print("\n--- Serialization Tests ---")
    
    # JSON serialization
    json_str = quote.to_json()
    print(f"JSON length: {len(json_str)} characters")
    
    # Redis value serialization
    redis_value = quote.to_redis_value()
    print(f"Redis value length: {len(redis_value)} characters")
    
    # Round-trip test
    reconstructed = StockQuote.from_redis_value(redis_value)
    print(f"Round-trip successful: {reconstructed.symbol == quote.symbol}")
    print(f"Timestamp preserved: {reconstructed.timestamp == quote.timestamp}")
    
    return quote


def demo_cache_operations_mock():
    """Demonstrate cache operations with mock Redis (no server required)."""
    print("\n=== Cache Operations Demo (Mock) ===")
    
    # This would normally connect to Redis, but we'll show the interface
    print("Redis Manager Interface:")
    print("- set_stock_data(symbol, quote, ttl=300)")
    print("- get_stock_data(symbol) -> StockQuote | None")
    print("- delete_stock_data(symbol) -> bool")
    print("- exists(symbol) -> bool")
    print("- get_ttl(symbol) -> int")
    print("- get_cache_info() -> dict")
    
    # Show configuration
    redis_config = Config.get_redis_config()
    print(f"\nRedis Configuration:")
    for key, value in redis_config.items():
        print(f"  {key}: {value}")


def demo_cache_operations_real():
    """Demonstrate real cache operations (requires Redis server)."""
    print("\n=== Real Cache Operations Demo ===")
    
    try:
        # Initialize Redis manager
        redis_config = Config.get_redis_config()
        cache_manager = RedisManager(**redis_config)
        
        # Create sample quote
        quote = StockQuote(
            symbol='500325',
            company_name='Reliance Industries Ltd',
            current_price=2501.50,
            change=1.50,
            percent_change=0.06,
            volume=1000000,
            timestamp=datetime.now()
        )
        
        print("Testing cache operations...")
        
        # Test set operation
        success = cache_manager.set_stock_data('500325', quote, ttl=60)
        print(f"Set operation: {'Success' if success else 'Failed'}")
        
        # Test get operation
        cached_quote = cache_manager.get_stock_data('500325')
        if cached_quote:
            print(f"Get operation: Success - {cached_quote.symbol}")
            print(f"Price matches: {cached_quote.current_price == quote.current_price}")
        else:
            print("Get operation: Failed")
        
        # Test exists operation
        exists = cache_manager.exists('500325')
        print(f"Exists check: {exists}")
        
        # Test TTL
        ttl = cache_manager.get_ttl('500325')
        print(f"TTL: {ttl} seconds")
        
        # Test cache info
        info = cache_manager.get_cache_info()
        if info:
            print(f"Cache info: {len(info)} metrics available")
            print(f"  Memory used: {info.get('used_memory', 'N/A')}")
        
        # Test delete operation
        deleted = cache_manager.delete_stock_data('500325')
        print(f"Delete operation: {'Success' if deleted else 'Failed'}")
        
        # Verify deletion
        exists_after = cache_manager.exists('500325')
        print(f"Exists after delete: {exists_after}")
        
        cache_manager.close()
        print("Cache operations completed successfully!")
        
    except Exception as e:
        print(f"Cache operations failed: {e}")
        print("This is expected if Redis server is not running.")
        print("To test with real Redis:")
        print("1. Install Redis server")
        print("2. Start Redis: redis-server")
        print("3. Run this demo again")


if __name__ == "__main__":
    print("BSE Data Optimization - Redis Cache Infrastructure Demo")
    print("=" * 60)
    
    # Demo 1: StockQuote serialization (always works)
    sample_quote = demo_stock_quote_serialization()
    
    # Demo 2: Cache interface (always works)
    demo_cache_operations_mock()
    
    # Demo 3: Real cache operations (requires Redis server)
    demo_cache_operations_real()
    
    print("\n" + "=" * 60)
    print("Demo completed!")
    print("\nNext steps:")
    print("1. Install and start Redis server for full functionality")
    print("2. Run the unit tests: python -m pytest tests/ -v")
    print("3. Integrate cache manager into your Flask application")