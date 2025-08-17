#!/usr/bin/env python3
"""
Compression Integration Demo

This demo shows how the CompressionService integrates with the OptimizedWebSocketService
to provide efficient real-time data delivery with compression and delta updates.
"""

import sys
import os
import time
import json
from datetime import datetime
from unittest.mock import Mock

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.compression_service import CompressionService
from services.optimized_websocket_service import OptimizedWebSocketService
from models.stock_quote import StockQuote


def create_mock_socketio():
    """Create a mock SocketIO for demonstration."""
    mock_socketio = Mock()
    mock_socketio.emit = Mock()
    return mock_socketio


def create_sample_stock_quotes():
    """Create sample stock quotes for demonstration."""
    return [
        StockQuote(
            symbol="500325",
            company_name="Reliance Industries Limited",
            current_price=2501.50,
            change=1.50,
            percent_change=0.06,
            volume=1234567,
            timestamp=datetime.now(),
            bid_price=2501.00,
            ask_price=2502.00,
            high=2505.00,
            low=2498.00
        ),
        StockQuote(
            symbol="500001",
            company_name="Tata Consultancy Services Limited",
            current_price=3456.75,
            change=-12.25,
            percent_change=-0.35,
            volume=987654,
            timestamp=datetime.now(),
            bid_price=3456.00,
            ask_price=3457.00,
            high=3470.00,
            low=3450.00
        )
    ]


def demo_compression_integration():
    """Demonstrate compression service integration with WebSocket service."""
    print("=" * 60)
    print("COMPRESSION INTEGRATION DEMO")
    print("=" * 60)
    
    # Create services
    mock_socketio = create_mock_socketio()
    compression_service = CompressionService()
    websocket_service = OptimizedWebSocketService(mock_socketio, compression_service)
    
    # Set up mock clients with different capabilities
    client1 = "client_compression_enabled"
    client2 = "client_basic"
    
    # Client 1: Full optimization support
    websocket_service.handle_client_capabilities_direct({
        'supports_compression': True,
        'supports_delta_updates': True,
        'supports_batch_updates': True,
        'max_message_size': 128 * 1024,
        'preferred_compression': 'msgpack'
    }, client1)
    
    # Client 2: Basic support only
    websocket_service.handle_client_capabilities_direct({
        'supports_compression': False,
        'supports_delta_updates': False,
        'supports_batch_updates': False,
        'max_message_size': 64 * 1024,
        'preferred_compression': 'none'
    }, client2)
    
    # Set up subscriptions
    symbol = "500325"
    websocket_service.websocket_manager.symbol_subscribers = {
        symbol: {client1, client2}
    }
    websocket_service.websocket_manager.connected_clients = {client1, client2}
    
    print(f"Set up 2 clients with different capabilities:")
    print(f"  {client1}: Full optimization support")
    print(f"  {client2}: Basic support only")
    print()
    
    # Create sample stock data
    stock_quotes = create_sample_stock_quotes()
    stock_data = stock_quotes[0]
    
    print(f"Sending stock update for {symbol}...")
    
    # Send initial update
    websocket_service.send_optimized_stock_update(symbol, stock_data)
    
    # Simulate price changes and send delta updates
    for i in range(3):
        # Modify price
        stock_data.current_price += 0.50
        stock_data.change += 0.50
        stock_data.percent_change = (stock_data.change / (stock_data.current_price - stock_data.change)) * 100
        stock_data.timestamp = datetime.now()
        
        print(f"Update {i+1}: Price changed to {stock_data.current_price}")
        websocket_service.send_optimized_stock_update(symbol, stock_data)
    
    # Get optimization statistics
    stats = websocket_service.get_optimization_stats()
    
    print("\nOptimization Statistics:")
    print(f"  Compression stats:")
    print(f"    Total compressions: {stats['compression']['total_compressions']}")
    print(f"    Delta updates: {stats['compression']['delta_updates']}")
    print(f"    Full updates: {stats['compression']['full_updates']}")
    print(f"    Average compression ratio: {stats['compression']['average_compression_ratio']:.1f}%")
    
    print(f"  Client capabilities:")
    print(f"    Total clients: {stats['client_capabilities']['total_clients']}")
    print(f"    Compression enabled: {stats['client_capabilities']['compression_enabled']}")
    print(f"    Delta enabled: {stats['client_capabilities']['delta_enabled']}")
    print(f"    Batch enabled: {stats['client_capabilities']['batch_enabled']}")
    
    print(f"  WebSocket calls made: {mock_socketio.emit.call_count}")
    print()


def demo_batch_compression():
    """Demonstrate batch compression with multiple updates."""
    print("=" * 60)
    print("BATCH COMPRESSION DEMO")
    print("=" * 60)
    
    # Create services
    mock_socketio = create_mock_socketio()
    compression_service = CompressionService()
    websocket_service = OptimizedWebSocketService(mock_socketio, compression_service)
    
    # Set up client with batch support
    client_id = "batch_client"
    websocket_service.handle_client_capabilities_direct({
        'supports_compression': True,
        'supports_delta_updates': True,
        'supports_batch_updates': True,
        'max_message_size': 256 * 1024,
        'preferred_compression': 'msgpack'
    }, client_id)
    
    # Set up subscriptions for multiple symbols
    symbols = ["500325", "500001"]
    websocket_service.websocket_manager.symbol_subscribers = {
        symbols[0]: {client_id},
        symbols[1]: {client_id}
    }
    websocket_service.websocket_manager.connected_clients = {client_id}
    
    print(f"Set up batch client subscribed to {len(symbols)} symbols")
    
    # Create multiple updates
    stock_quotes = create_sample_stock_quotes()
    updates = []
    
    for i, stock_quote in enumerate(stock_quotes):
        for j in range(3):  # 3 updates per stock
            # Simulate price changes
            stock_quote.current_price += (j * 0.25)
            stock_quote.change += (j * 0.25)
            stock_quote.timestamp = datetime.now()
            
            updates.append({
                'symbol': stock_quote.symbol,
                'data': stock_quote
            })
    
    print(f"Created {len(updates)} stock updates")
    
    # Send bulk updates without auto-flush to see batching
    websocket_service._send_bulk_updates_to_client(client_id, updates, auto_flush=False)
    
    print(f"Pending batch size: {len(websocket_service.pending_batches.get(client_id, []))}")
    
    # Now flush the batch
    websocket_service._flush_batch(client_id)
    
    print(f"Batch flushed - WebSocket calls made: {mock_socketio.emit.call_count}")
    
    # Show compression benefits
    stats = compression_service.get_compression_stats()
    print(f"Compression benefits:")
    print(f"  Total compressions: {stats['total_compressions']}")
    print(f"  Average compression ratio: {stats['average_compression_ratio']:.1f}%")
    print(f"  Total size reduction: {stats['total_original_size'] - stats['total_compressed_size']} bytes")
    print()


def demo_performance_comparison():
    """Compare performance with and without compression."""
    print("=" * 60)
    print("PERFORMANCE COMPARISON")
    print("=" * 60)
    
    # Test data
    stock_quotes = create_sample_stock_quotes()
    num_updates = 50
    
    print(f"Testing with {num_updates} stock updates...")
    
    # Test 1: Without compression
    print("\n1. Without compression:")
    start_time = time.time()
    
    mock_socketio1 = create_mock_socketio()
    websocket_service1 = OptimizedWebSocketService(mock_socketio1)
    
    client_id = "test_client"
    websocket_service1.handle_client_capabilities_direct({
        'supports_compression': False,
        'supports_delta_updates': False,
        'supports_batch_updates': False
    }, client_id)
    
    websocket_service1.websocket_manager.symbol_subscribers = {"500325": {client_id}}
    websocket_service1.websocket_manager.connected_clients = {client_id}
    
    for i in range(num_updates):
        stock_data = stock_quotes[0]
        stock_data.current_price += (i * 0.01)
        websocket_service1.send_optimized_stock_update("500325", stock_data)
    
    time1 = time.time() - start_time
    calls1 = mock_socketio1.emit.call_count
    
    print(f"   Time: {time1*1000:.2f} ms")
    print(f"   WebSocket calls: {calls1}")
    
    # Test 2: With full compression
    print("\n2. With full compression:")
    start_time = time.time()
    
    mock_socketio2 = create_mock_socketio()
    websocket_service2 = OptimizedWebSocketService(mock_socketio2)
    
    websocket_service2.handle_client_capabilities_direct({
        'supports_compression': True,
        'supports_delta_updates': True,
        'supports_batch_updates': True
    }, client_id)
    
    websocket_service2.websocket_manager.symbol_subscribers = {"500325": {client_id}}
    websocket_service2.websocket_manager.connected_clients = {client_id}
    
    for i in range(num_updates):
        stock_data = stock_quotes[0]
        stock_data.current_price += (i * 0.01)
        websocket_service2.send_optimized_stock_update("500325", stock_data)
    
    time2 = time.time() - start_time
    calls2 = mock_socketio2.emit.call_count
    stats2 = websocket_service2.get_optimization_stats()
    
    print(f"   Time: {time2*1000:.2f} ms")
    print(f"   WebSocket calls: {calls2}")
    print(f"   Delta updates: {stats2['compression']['delta_updates']}")
    print(f"   Compression ratio: {stats2['compression']['average_compression_ratio']:.1f}%")
    
    # Comparison
    print(f"\nComparison:")
    print(f"   Time improvement: {((time1 - time2) / time1) * 100:.1f}%")
    print(f"   Call reduction: {((calls1 - calls2) / calls1) * 100:.1f}%")
    print()


def main():
    """Run all integration demos."""
    print("BSE Data Optimization - Compression Integration Demo")
    print("This demo shows how compression integrates with WebSocket services")
    print()
    
    try:
        demo_compression_integration()
        demo_batch_compression()
        demo_performance_comparison()
        
        print("=" * 60)
        print("INTEGRATION DEMO COMPLETED SUCCESSFULLY")
        print("=" * 60)
        print("Key integration benefits demonstrated:")
        print("• Seamless compression integration with WebSocket service")
        print("• Client capability negotiation for optimal performance")
        print("• Automatic delta updates for bandwidth savings")
        print("• Batch processing for high-frequency updates")
        print("• Performance improvements with minimal overhead")
        
    except Exception as e:
        print(f"Demo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()