#!/usr/bin/env python3
"""
Cache Integration Demo

Demonstrates the integration between BatchDataFetcher, CacheManager, 
WebSocketManager, and CacheIntegrationService for real-time stock updates.
"""

import time
import logging
from datetime import datetime
from flask import Flask
from flask_socketio import SocketIO

from cache.redis_manager import RedisManager
from services.batch_data_fetcher import BatchDataFetcher, SymbolPriority
from services.websocket_manager import WebSocketManager
from services.cache_integration_service import CacheIntegrationService


def setup_logging():
    """Setup logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def create_demo_app():
    """Create Flask app with SocketIO for demo."""
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'demo_secret_key'
    socketio = SocketIO(app, cors_allowed_origins="*")
    return app, socketio


def main():
    """Main demo function."""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("Starting Cache Integration Demo")
    
    try:
        # Initialize components
        logger.info("Initializing components...")
        
        # Cache Manager (Redis)
        cache_manager = RedisManager(
            host='localhost',
            port=6379,
            db=0,
            default_ttl=300  # 5 minutes
        )
        
        # Batch Data Fetcher
        batch_fetcher = BatchDataFetcher(
            max_batch_size=10,
            max_retries=3
        )
        
        # Flask app and WebSocket Manager
        app, socketio = create_demo_app()
        websocket_manager = WebSocketManager(socketio)
        
        # Integration Service
        integration_service = CacheIntegrationService(
            cache_manager=cache_manager,
            batch_fetcher=batch_fetcher,
            websocket_manager=websocket_manager
        )
        
        logger.info("Components initialized successfully")
        
        # Add some essential stocks for demo
        essential_stocks = [
            ("500325", SymbolPriority.HIGH),    # Reliance Industries
            ("500209", SymbolPriority.HIGH),    # Infosys
            ("532540", SymbolPriority.MEDIUM),  # TCS
            ("500180", SymbolPriority.MEDIUM),  # HDFC Bank
            ("532215", SymbolPriority.LOW)      # Axis Bank
        ]
        
        logger.info("Adding essential stocks...")
        for symbol, priority in essential_stocks:
            integration_service.add_essential_stock(symbol, priority)
            logger.info(f"Added {symbol} with priority {priority.name}")
        
        # Warm cache for essential stocks
        logger.info("Warming cache for essential stocks...")
        warm_results = integration_service.warm_cache_for_essentials()
        logger.info(f"Cache warming results: {warm_results}")
        
        # Start periodic cache warming
        logger.info("Starting periodic cache warming...")
        integration_service.start_periodic_cache_warming(interval=60)  # Every minute
        
        # Start periodic batch updates
        logger.info("Starting periodic batch updates...")
        batch_fetcher.schedule_periodic_updates(interval=10)  # Every 10 seconds
        
        # Demo WebSocket endpoint
        @socketio.on('connect')
        def handle_connect():
            logger.info(f"Client connected")
        
        @socketio.on('subscribe_demo')
        def handle_subscribe_demo(data):
            symbols = data.get('symbols', [])
            logger.info(f"Demo subscription request for symbols: {symbols}")
            
            # Add symbols to batch fetcher if not already watched
            for symbol in symbols:
                if symbol not in batch_fetcher.watched_symbols:
                    batch_fetcher.add_symbol_to_watch(symbol, SymbolPriority.MEDIUM)
        
        # Demo: Simulate some cache operations
        logger.info("Running demo operations...")
        
        # Test cache hit/miss scenarios
        for symbol, _ in essential_stocks[:3]:
            logger.info(f"Testing cache operations for {symbol}")
            
            # Get data (should be cache hit after warming)
            stock_data = integration_service.get_stock_data(symbol, fetch_if_missing=True)
            if stock_data:
                logger.info(f"Retrieved data for {symbol}: {stock_data.current_price}")
            
            # Test invalidation and refresh
            logger.info(f"Testing invalidation and refresh for {symbol}")
            refresh_results = integration_service.invalidate_and_refresh([symbol])
            logger.info(f"Refresh results: {refresh_results}")
        
        # Display performance stats
        logger.info("Performance Statistics:")
        batch_stats = batch_fetcher.get_performance_stats()
        integration_stats = integration_service.get_performance_stats()
        cache_status = integration_service.get_cache_status()
        
        logger.info(f"Batch Fetcher Stats: {batch_stats}")
        logger.info(f"Integration Stats: {integration_stats}")
        logger.info(f"Cache Status: {cache_status}")
        
        # Run Flask app for WebSocket demo
        logger.info("Starting Flask app for WebSocket demo...")
        logger.info("Connect to http://localhost:5000 to test WebSocket functionality")
        logger.info("Press Ctrl+C to stop the demo")
        
        # Add a simple HTML page for testing
        @app.route('/')
        def index():
            return '''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Cache Integration Demo</title>
                <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
            </head>
            <body>
                <h1>BSE Cache Integration Demo</h1>
                <div id="status">Connecting...</div>
                <div id="updates"></div>
                
                <script>
                    const socket = io();
                    
                    socket.on('connect', function() {
                        document.getElementById('status').innerHTML = 'Connected';
                        
                        // Subscribe to demo symbols
                        socket.emit('subscribe_demo', {
                            symbols: ['500325', '500209', '532540']
                        });
                    });
                    
                    socket.on('stock_update', function(data) {
                        const updatesDiv = document.getElementById('updates');
                        const updateElement = document.createElement('div');
                        updateElement.innerHTML = `
                            <strong>${data.symbol}</strong>: 
                            ${data.data.current_price} 
                            (${data.data.change > 0 ? '+' : ''}${data.data.change})
                            - ${data.timestamp}
                        `;
                        updatesDiv.insertBefore(updateElement, updatesDiv.firstChild);
                        
                        // Keep only last 10 updates
                        while (updatesDiv.children.length > 10) {
                            updatesDiv.removeChild(updatesDiv.lastChild);
                        }
                    });
                    
                    socket.on('disconnect', function() {
                        document.getElementById('status').innerHTML = 'Disconnected';
                    });
                </script>
            </body>
            </html>
            '''
        
        # Run the app
        socketio.run(app, host='0.0.0.0', port=5000, debug=False)
        
    except KeyboardInterrupt:
        logger.info("Demo stopped by user")
    except Exception as e:
        logger.error(f"Demo error: {e}")
        raise
    finally:
        # Cleanup
        logger.info("Cleaning up...")
        if 'integration_service' in locals():
            integration_service.stop()
        if 'cache_manager' in locals():
            cache_manager.close()
        logger.info("Demo cleanup completed")


if __name__ == "__main__":
    main()