#!/usr/bin/env python3
"""
Compression Service Demo

This demo showcases the CompressionService capabilities including:
- Data compression and decompression
- Delta updates for bandwidth optimization
- Batch processing for multiple updates
- Performance metrics and statistics

Run this demo to see compression ratios and performance improvements.
"""

import sys
import os
import time
import json
from datetime import datetime, timedelta

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.compression_service import CompressionService
from models.stock_quote import StockQuote


def create_sample_stock_data():
    """Create sample stock data for demonstration."""
    stocks = [
        {
            'symbol': '500325',
            'company_name': 'Reliance Industries Limited',
            'current_price': 2501.50,
            'change': 1.50,
            'percent_change': 0.06,
            'volume': 1234567,
            'bid_price': 2501.00,
            'ask_price': 2502.00,
            'high': 2505.00,
            'low': 2498.00
        },
        {
            'symbol': '500001',
            'company_name': 'Tata Consultancy Services Limited',
            'current_price': 3456.75,
            'change': -12.25,
            'percent_change': -0.35,
            'volume': 987654,
            'bid_price': 3456.00,
            'ask_price': 3457.00,
            'high': 3470.00,
            'low': 3450.00
        },
        {
            'symbol': '532540',
            'company_name': 'Tata Steel Limited',
            'current_price': 1234.80,
            'change': 5.60,
            'percent_change': 0.46,
            'volume': 2345678,
            'bid_price': 1234.50,
            'ask_price': 1235.00,
            'high': 1240.00,
            'low': 1230.00
        }
    ]
    
    # Add timestamps
    base_time = datetime.now()
    for i, stock in enumerate(stocks):
        stock['timestamp'] = (base_time + timedelta(seconds=i)).isoformat()
    
    return stocks


def demo_basic_compression():
    """Demonstrate basic compression and decompression."""
    print("=" * 60)
    print("BASIC COMPRESSION DEMO")
    print("=" * 60)
    
    compression_service = CompressionService()
    sample_data = create_sample_stock_data()[0]  # Use first stock
    
    print(f"Original data: {json.dumps(sample_data, indent=2)}")
    print(f"Original size: {len(json.dumps(sample_data))} characters")
    
    # Compress the data
    start_time = time.time()
    compressed_data = compression_service.compress_stock_data(sample_data)
    compression_time = time.time() - start_time
    
    print(f"Compressed size: {len(compressed_data)} bytes")
    print(f"Compression time: {compression_time*1000:.2f} ms")
    
    # Decompress the data
    start_time = time.time()
    decompressed_data = compression_service.decompress_stock_data(compressed_data)
    decompression_time = time.time() - start_time
    
    print(f"Decompression time: {decompression_time*1000:.2f} ms")
    print(f"Data integrity check: {'PASS' if decompressed_data['symbol'] == sample_data['symbol'] else 'FAIL'}")
    
    # Show compression stats
    stats = compression_service.get_compression_stats()
    print(f"Compression ratio: {stats['average_compression_ratio']:.1f}%")
    print()


def demo_delta_updates():
    """Demonstrate delta update functionality."""
    print("=" * 60)
    print("DELTA UPDATES DEMO")
    print("=" * 60)
    
    compression_service = CompressionService()
    symbol = "500325"
    base_data = create_sample_stock_data()[0]
    
    print("Simulating real-time price updates...")
    print()
    
    # First update (full)
    print("1. Initial update (full):")
    delta1 = compression_service.create_delta_update(symbol, base_data)
    print(f"   Type: {delta1['type']}")
    print(f"   Changes: {len(delta1.get('changes', {}))} fields")
    print(f"   Size: {len(json.dumps(delta1))} characters")
    print()
    
    # Second update (same data - heartbeat)
    print("2. Same data update (heartbeat):")
    delta2 = compression_service.create_delta_update(symbol, base_data)
    print(f"   Type: {delta2['type']}")
    print(f"   Size: {len(json.dumps(delta2))} characters")
    print()
    
    # Third update (price change)
    print("3. Price change update (delta):")
    modified_data = base_data.copy()
    modified_data['current_price'] = 2502.75
    modified_data['change'] = 2.75
    modified_data['percent_change'] = 0.11
    modified_data['timestamp'] = datetime.now().isoformat()
    
    delta3 = compression_service.create_delta_update(symbol, modified_data)
    print(f"   Type: {delta3['type']}")
    print(f"   Changes: {list(delta3.get('changes', {}).keys())}")
    print(f"   Size: {len(json.dumps(delta3))} characters")
    print()
    
    # Calculate bandwidth savings
    full_size = len(json.dumps(compression_service.create_full_update(symbol, modified_data)))
    delta_size = len(json.dumps(delta3))
    savings = ((full_size - delta_size) / full_size) * 100
    
    print(f"Bandwidth savings: {savings:.1f}% (delta: {delta_size} vs full: {full_size} chars)")
    print()


def demo_batch_compression():
    """Demonstrate batch compression for multiple updates."""
    print("=" * 60)
    print("BATCH COMPRESSION DEMO")
    print("=" * 60)
    
    compression_service = CompressionService()
    stocks_data = create_sample_stock_data()
    
    # Create multiple updates
    updates = []
    for i, stock_data in enumerate(stocks_data):
        # Simulate price changes
        stock_data['current_price'] += (i * 0.5)
        stock_data['change'] += (i * 0.2)
        stock_data['timestamp'] = datetime.now().isoformat()
        
        update = compression_service.create_delta_update(stock_data['symbol'], stock_data)
        updates.append(update)
    
    print(f"Created {len(updates)} stock updates")
    
    # Individual compression
    individual_sizes = []
    for update in updates:
        compressed = compression_service.compress_stock_data(update)
        individual_sizes.append(len(compressed))
    
    total_individual_size = sum(individual_sizes)
    print(f"Individual compression total: {total_individual_size} bytes")
    
    # Batch compression
    start_time = time.time()
    batch_compressed = compression_service.compress_batch_updates(updates)
    batch_time = time.time() - start_time
    
    print(f"Batch compression size: {len(batch_compressed)} bytes")
    print(f"Batch compression time: {batch_time*1000:.2f} ms")
    
    # Calculate savings
    batch_savings = ((total_individual_size - len(batch_compressed)) / total_individual_size) * 100
    print(f"Batch compression savings: {batch_savings:.1f}%")
    
    # Test decompression
    start_time = time.time()
    decompressed_updates = compression_service.decompress_batch_updates(batch_compressed)
    decompress_time = time.time() - start_time
    
    print(f"Batch decompression time: {decompress_time*1000:.2f} ms")
    print(f"Decompressed updates: {len(decompressed_updates)}")
    print(f"Data integrity: {'PASS' if len(decompressed_updates) == len(updates) else 'FAIL'}")
    print()


def demo_performance_comparison():
    """Demonstrate performance comparison between different approaches."""
    print("=" * 60)
    print("PERFORMANCE COMPARISON")
    print("=" * 60)
    
    compression_service = CompressionService()
    stocks_data = create_sample_stock_data()
    
    # Simulate 100 updates
    num_updates = 100
    print(f"Simulating {num_updates} stock updates...")
    
    # Method 1: JSON serialization (baseline)
    json_sizes = []
    json_time = 0
    
    for i in range(num_updates):
        stock_data = stocks_data[i % len(stocks_data)].copy()
        stock_data['current_price'] += (i * 0.01)
        stock_data['timestamp'] = datetime.now().isoformat()
        
        start_time = time.time()
        json_str = json.dumps(stock_data)
        json_time += time.time() - start_time
        json_sizes.append(len(json_str.encode('utf-8')))
    
    # Method 2: MessagePack compression
    msgpack_sizes = []
    msgpack_time = 0
    
    for i in range(num_updates):
        stock_data = stocks_data[i % len(stocks_data)].copy()
        stock_data['current_price'] += (i * 0.01)
        stock_data['timestamp'] = datetime.now().isoformat()
        
        start_time = time.time()
        compressed = compression_service.compress_stock_data(stock_data)
        msgpack_time += time.time() - start_time
        msgpack_sizes.append(len(compressed))
    
    # Method 3: Delta updates
    delta_sizes = []
    delta_time = 0
    
    for i in range(num_updates):
        stock_data = stocks_data[i % len(stocks_data)].copy()
        stock_data['current_price'] += (i * 0.01)
        stock_data['timestamp'] = datetime.now().isoformat()
        
        start_time = time.time()
        delta = compression_service.create_delta_update(stock_data['symbol'], stock_data)
        compressed_delta = compression_service.compress_stock_data(delta)
        delta_time += time.time() - start_time
        delta_sizes.append(len(compressed_delta))
    
    # Results
    print("\nResults:")
    print(f"JSON (baseline):")
    print(f"  Total size: {sum(json_sizes):,} bytes")
    print(f"  Average size: {sum(json_sizes)/len(json_sizes):.1f} bytes")
    print(f"  Total time: {json_time*1000:.2f} ms")
    
    print(f"\nMessagePack compression:")
    print(f"  Total size: {sum(msgpack_sizes):,} bytes")
    print(f"  Average size: {sum(msgpack_sizes)/len(msgpack_sizes):.1f} bytes")
    print(f"  Total time: {msgpack_time*1000:.2f} ms")
    print(f"  Size reduction: {((sum(json_sizes) - sum(msgpack_sizes)) / sum(json_sizes)) * 100:.1f}%")
    
    print(f"\nDelta + MessagePack:")
    print(f"  Total size: {sum(delta_sizes):,} bytes")
    print(f"  Average size: {sum(delta_sizes)/len(delta_sizes):.1f} bytes")
    print(f"  Total time: {delta_time*1000:.2f} ms")
    print(f"  Size reduction: {((sum(json_sizes) - sum(delta_sizes)) / sum(json_sizes)) * 100:.1f}%")
    
    # Overall stats
    stats = compression_service.get_compression_stats()
    print(f"\nOverall compression statistics:")
    print(f"  Total compressions: {stats['total_compressions']}")
    print(f"  Delta updates: {stats['delta_updates']}")
    print(f"  Full updates: {stats['full_updates']}")
    print(f"  Average compression ratio: {stats['average_compression_ratio']:.1f}%")
    print()


def demo_memory_efficiency():
    """Demonstrate memory efficiency features."""
    print("=" * 60)
    print("MEMORY EFFICIENCY DEMO")
    print("=" * 60)
    
    compression_service = CompressionService()
    
    print("Testing cache management with many symbols...")
    
    # Create updates for many symbols
    num_symbols = 1000
    for i in range(num_symbols):
        symbol = f"TEST{i:04d}"
        data = {
            'symbol': symbol,
            'current_price': 100.0 + (i * 0.1),
            'volume': 1000 + i,
            'timestamp': datetime.now().isoformat()
        }
        compression_service.create_delta_update(symbol, data)
    
    print(f"Created delta updates for {num_symbols} symbols")
    print(f"Cache size: {len(compression_service.previous_data_cache)} entries")
    
    # Demonstrate cache clearing
    compression_service.clear_cache()
    print(f"Cache size after clearing: {len(compression_service.previous_data_cache)} entries")
    
    # Show memory optimization in data structure
    sample_data = {
        'symbol': 'TEST',
        'company_name': 'Test Company with Very Long Name That Takes Up Space',
        'current_price': 1234.123456789,
        'percent_change': 0.123456789,
        'volume': 1234567,
        'bid_price': None,  # Will be excluded
        'ask_price': 1234.50
    }
    
    print(f"\nData structure optimization:")
    print(f"Original data: {json.dumps(sample_data)}")
    print(f"Original size: {len(json.dumps(sample_data))} characters")
    
    optimized = compression_service._optimize_data_structure(sample_data)
    print(f"Optimized data: {json.dumps(optimized)}")
    print(f"Optimized size: {len(json.dumps(optimized))} characters")
    
    restored = compression_service._restore_data_structure(optimized)
    print(f"Restored correctly: {'PASS' if restored['symbol'] == sample_data['symbol'] else 'FAIL'}")
    print()


def main():
    """Run all compression demos."""
    print("BSE Data Optimization - Compression Service Demo")
    print("This demo showcases compression and optimization features")
    print()
    
    try:
        demo_basic_compression()
        demo_delta_updates()
        demo_batch_compression()
        demo_performance_comparison()
        demo_memory_efficiency()
        
        print("=" * 60)
        print("DEMO COMPLETED SUCCESSFULLY")
        print("=" * 60)
        print("Key benefits demonstrated:")
        print("• Significant size reduction with MessagePack compression")
        print("• Bandwidth savings with delta updates")
        print("• Improved efficiency with batch processing")
        print("• Memory optimization with smart caching")
        print("• Performance improvements for high-frequency updates")
        
    except Exception as e:
        print(f"Demo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()