# server.py
from flask import Flask, jsonify, request, Blueprint
from flask_cors import CORS
from flask_socketio import SocketIO
from bsedata.bse import BSE
from services.websocket_manager import WebSocketManager
from services.monitoring_service import MonitoringService, AlertLevel
from services.error_handling_service import ErrorHandlingService, FallbackStrategy, with_error_handling
from services.cache_integration_service import CacheIntegrationService
from services.batch_data_fetcher import BatchDataFetcher
from cache.redis_manager import RedisManager
from models.stock_quote import StockQuote
import logging
import time
from datetime import datetime
from typing import List, Dict, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'  # Change this in production
CORS(app, resources={r"/*": {"origins": "*"}})  # Enable CORS for frontend connection

# Initialize SocketIO with CORS support
socketio = SocketIO(app, cors_allowed_origins="*", logger=True, engineio_logger=True)

# Initialize services
websocket_manager = WebSocketManager(socketio)
monitoring_service = MonitoringService()
error_handler = ErrorHandlingService()

# Initialize BSE client
b = BSE(update_codes = True)   # loads all stock codes

# Initialize Redis cache (with error handling)
try:
    cache_manager = RedisManager()
    error_handler.register_service("cache", FallbackStrategy.LAST_KNOWN_GOOD)
    logger.info("Redis cache initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Redis cache: {e}")
    cache_manager = None
    error_handler.record_error("cache", e, "critical")

# Initialize batch data fetcher and cache integration
batch_fetcher = BatchDataFetcher(b)
cache_integration = None
if cache_manager:
    try:
        cache_integration = CacheIntegrationService(
            cache_manager=cache_manager,
            batch_fetcher=batch_fetcher,
            websocket_manager=websocket_manager
        )
        logger.info("Cache integration service initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize cache integration: {e}")
        error_handler.record_error("cache_integration", e, "critical")

# Register services for monitoring
error_handler.register_service("bse_api", FallbackStrategy.CACHE_ONLY)
error_handler.register_service("websocket", FallbackStrategy.FAIL_FAST)

# Add circuit breakers
monitoring_service.add_circuit_breaker("bse_api", failure_threshold=5, recovery_timeout=60)
monitoring_service.add_circuit_breaker("cache", failure_threshold=3, recovery_timeout=30)

# Create API blueprints for versioning
api_v1 = Blueprint('api_v1', __name__, url_prefix='/api/v1')
api_v2 = Blueprint('api_v2', __name__, url_prefix='/api/v2')

# Legacy API routes (maintain backward compatibility)
legacy_api = Blueprint('legacy_api', __name__, url_prefix='/api')

# Legacy API routes (v1 - backward compatibility)
@legacy_api.route("/stocks")
def get_stocks_legacy():
    """Legacy endpoint for getting stock list."""
    return get_stocks_v1()

@legacy_api.route("/quote/<string:symbol>")
def quote_legacy(symbol):
    """Legacy endpoint for getting single stock quote."""
    start_time = time.time()
    
    try:
        # Try cache integration service first
        stock_quote = None
        if cache_integration:
            stock_quote = cache_integration.get_stock_data(symbol, fetch_if_missing=True)
        
        if stock_quote:
            # Convert StockQuote to legacy response format (no version field)
            response_data = {
                "code": symbol,
                "company": stock_quote.company_name,
                "price": stock_quote.current_price,
                "change": stock_quote.change,
                "pChange": stock_quote.percent_change,
                "timestamp": stock_quote.timestamp.isoformat(),
                "cached": True
            }
            
            duration = time.time() - start_time
            monitoring_service.metrics.record_timing("api_response_time", duration, {"endpoint": "quote", "version": "legacy"})
            monitoring_service.metrics.record_counter("api_requests_success", 1, {"endpoint": "quote", "version": "legacy"})
            
            return jsonify(response_data)
        
        # Fallback to direct BSE API call
        circuit_breaker = monitoring_service.get_circuit_breaker("bse_api")
        
        if circuit_breaker:
            q = circuit_breaker.call(b.getQuote, symbol)
        else:
            q = b.getQuote(symbol)
        
        # Record successful API call
        duration = time.time() - start_time
        monitoring_service.metrics.record_timing("api_response_time", duration, {"endpoint": "quote", "version": "legacy"})
        monitoring_service.metrics.record_counter("api_requests_success", 1, {"endpoint": "quote", "version": "legacy"})
        error_handler.record_success("bse_api", q)
        
        response_data = {
            "code": symbol,
            "company": q["companyName"],
            "price": q["currentValue"],
            "change": q["change"],
            "pChange": q["pChange"],
            "timestamp": datetime.now().isoformat(),
            "cached": False
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        duration = time.time() - start_time
        monitoring_service.metrics.record_timing("api_response_time", duration, {"endpoint": "quote", "version": "legacy", "status": "error"})
        monitoring_service.metrics.record_counter("api_requests_error", 1, {"endpoint": "quote", "version": "legacy"})
        
        # Record error and attempt fallback
        error_handler.record_error("bse_api", e)
        
        # Try to get cached data as fallback
        if cache_manager:
            try:
                cached_data = cache_manager.get_stock_data(symbol)
                if cached_data:
                    monitoring_service.metrics.record_counter("cache_hits", 1)
                    if isinstance(cached_data, dict):
                        cached_data["cached"] = True
                        cached_data["cache_warning"] = "Live data unavailable, serving cached data"
                        return jsonify(cached_data)
                else:
                    monitoring_service.metrics.record_counter("cache_misses", 1)
            except Exception as cache_error:
                logger.error(f"Cache fallback failed: {cache_error}")
                error_handler.record_error("cache", cache_error)
        
        # If no fallback available, return error
        logger.error(f"Failed to get quote for {symbol}: {e}")
        return jsonify({
            "error": str(e),
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "fallback_attempted": cache_manager is not None
        }), 500

# API v1 routes
@api_v1.route("/stocks")
def get_stocks_v1():
    """Get list of available stocks."""
    try:
        import json
        with open('stk.json', 'r') as f:
            stocks = json.load(f)
        return jsonify({
            "version": "1.0",
            "data": stocks,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            "version": "1.0",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 400

@api_v1.route("/quote/<string:symbol>")
def quote_v1(symbol):
    """Get single stock quote with cache integration."""
    start_time = time.time()
    
    try:
        # Try cache integration service first
        stock_quote = None
        if cache_integration:
            stock_quote = cache_integration.get_stock_data(symbol, fetch_if_missing=True)
        
        if stock_quote:
            # Convert StockQuote to response format
            response_data = {
                "version": "1.0",
                "code": symbol,
                "company": stock_quote.company_name,
                "price": stock_quote.current_price,
                "change": stock_quote.change,
                "pChange": stock_quote.percent_change,
                "timestamp": stock_quote.timestamp.isoformat(),
                "cached": True
            }
            
            duration = time.time() - start_time
            monitoring_service.metrics.record_timing("api_response_time", duration, {"endpoint": "quote", "version": "v1"})
            monitoring_service.metrics.record_counter("api_requests_success", 1, {"endpoint": "quote", "version": "v1"})
            
            return jsonify(response_data)
        
        # Fallback to direct BSE API call
        circuit_breaker = monitoring_service.get_circuit_breaker("bse_api")
        
        if circuit_breaker:
            q = circuit_breaker.call(b.getQuote, symbol)
        else:
            q = b.getQuote(symbol)
        
        # Record successful API call
        duration = time.time() - start_time
        monitoring_service.metrics.record_timing("api_response_time", duration, {"endpoint": "quote", "version": "v1"})
        monitoring_service.metrics.record_counter("api_requests_success", 1, {"endpoint": "quote", "version": "v1"})
        error_handler.record_success("bse_api", q)
        
        response_data = {
            "version": "1.0",
            "code": symbol,
            "company": q["companyName"],
            "price": q["currentValue"],
            "change": q["change"],
            "pChange": q["pChange"],
            "timestamp": datetime.now().isoformat(),
            "cached": False
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        duration = time.time() - start_time
        monitoring_service.metrics.record_timing("api_response_time", duration, {"endpoint": "quote", "version": "v1", "status": "error"})
        monitoring_service.metrics.record_counter("api_requests_error", 1, {"endpoint": "quote", "version": "v1"})
        
        # Record error and attempt fallback
        error_handler.record_error("bse_api", e)
        
        # Try to get cached data as fallback
        if cache_manager:
            try:
                cached_data = cache_manager.get_stock_data(symbol)
                if cached_data:
                    monitoring_service.metrics.record_counter("cache_hits", 1)
                    if isinstance(cached_data, dict):
                        cached_data["version"] = "1.0"
                        cached_data["cached"] = True
                        cached_data["cache_warning"] = "Live data unavailable, serving cached data"
                        return jsonify(cached_data)
                else:
                    monitoring_service.metrics.record_counter("cache_misses", 1)
            except Exception as cache_error:
                logger.error(f"Cache fallback failed: {cache_error}")
                error_handler.record_error("cache", cache_error)
        
        # If no fallback available, return error
        logger.error(f"Failed to get quote for {symbol}: {e}")
        return jsonify({
            "version": "1.0",
            "error": str(e),
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "fallback_attempted": cache_manager is not None
        }), 500

# API v2 routes (enhanced features)
@api_v2.route("/stocks")
def get_stocks_v2():
    """Get list of available stocks with enhanced metadata."""
    try:
        import json
        with open('stk.json', 'r') as f:
            stocks = json.load(f)
        
        # Add cache status for each stock if available
        enhanced_stocks = []
        for stock in stocks:
            stock_data = dict(stock)
            if cache_manager and 'symbol' in stock:
                cached_quote = cache_manager.get_stock_data(stock['symbol'])
                stock_data['cached'] = cached_quote is not None
                if cached_quote and hasattr(cached_quote, 'timestamp'):
                    stock_data['last_updated'] = cached_quote.timestamp.isoformat()
            enhanced_stocks.append(stock_data)
        
        return jsonify({
            "version": "2.0",
            "data": enhanced_stocks,
            "total_count": len(enhanced_stocks),
            "timestamp": datetime.now().isoformat(),
            "cache_enabled": cache_manager is not None
        })
    except Exception as e:
        return jsonify({
            "version": "2.0",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 400

@api_v2.route("/quote/<string:symbol>")
def quote_v2(symbol):
    """Get single stock quote with enhanced data."""
    start_time = time.time()
    
    try:
        # Use cache integration service
        stock_quote = None
        if cache_integration:
            stock_quote = cache_integration.get_stock_data(symbol, fetch_if_missing=True)
        
        if stock_quote:
            response_data = {
                "version": "2.0",
                "symbol": symbol,
                "company_name": stock_quote.company_name,
                "current_price": stock_quote.current_price,
                "change": stock_quote.change,
                "percent_change": stock_quote.percent_change,
                "volume": stock_quote.volume,
                "timestamp": stock_quote.timestamp.isoformat(),
                "bid_price": stock_quote.bid_price,
                "ask_price": stock_quote.ask_price,
                "high": stock_quote.high,
                "low": stock_quote.low,
                "data_source": "cache_integrated"
            }
            
            duration = time.time() - start_time
            monitoring_service.metrics.record_timing("api_response_time", duration, {"endpoint": "quote", "version": "v2"})
            monitoring_service.metrics.record_counter("api_requests_success", 1, {"endpoint": "quote", "version": "v2"})
            
            return jsonify(response_data)
        
        # Fallback to direct API call
        return jsonify({
            "version": "2.0",
            "error": "Unable to fetch stock data",
            "symbol": symbol,
            "timestamp": datetime.now().isoformat()
        }), 500
        
    except Exception as e:
        duration = time.time() - start_time
        monitoring_service.metrics.record_timing("api_response_time", duration, {"endpoint": "quote", "version": "v2", "status": "error"})
        monitoring_service.metrics.record_counter("api_requests_error", 1, {"endpoint": "quote", "version": "v2"})
        
        logger.error(f"Failed to get quote for {symbol}: {e}")
        return jsonify({
            "version": "2.0",
            "error": str(e),
            "symbol": symbol,
            "timestamp": datetime.now().isoformat()
        }), 500

@api_v2.route("/quotes", methods=["POST"])
def batch_quotes_v2():
    """Get multiple stock quotes in a single request."""
    start_time = time.time()
    
    try:
        data = request.get_json()
        if not data or 'symbols' not in data:
            return jsonify({
                "version": "2.0",
                "error": "Missing 'symbols' in request body",
                "timestamp": datetime.now().isoformat()
            }), 400
        
        symbols = data['symbols']
        if not isinstance(symbols, list) or len(symbols) == 0:
            return jsonify({
                "version": "2.0",
                "error": "Symbols must be a non-empty list",
                "timestamp": datetime.now().isoformat()
            }), 400
        
        if len(symbols) > 50:  # Limit batch size
            return jsonify({
                "version": "2.0",
                "error": "Maximum 50 symbols allowed per batch request",
                "timestamp": datetime.now().isoformat()
            }), 400
        
        results = {}
        errors = {}
        
        # Use batch fetcher if available
        if batch_fetcher:
            batch_result = batch_fetcher.fetch_batch_quotes(symbols)
            
            for symbol in symbols:
                if symbol in batch_result.successful_quotes:
                    stock_quote = batch_result.successful_quotes[symbol]
                    results[symbol] = {
                        "symbol": symbol,
                        "company_name": stock_quote.company_name,
                        "current_price": stock_quote.current_price,
                        "change": stock_quote.change,
                        "percent_change": stock_quote.percent_change,
                        "volume": stock_quote.volume,
                        "timestamp": stock_quote.timestamp.isoformat(),
                        "bid_price": stock_quote.bid_price,
                        "ask_price": stock_quote.ask_price,
                        "high": stock_quote.high,
                        "low": stock_quote.low
                    }
                elif symbol in batch_result.failed_symbols:
                    errors[symbol] = batch_result.failed_symbols[symbol]
        
        duration = time.time() - start_time
        monitoring_service.metrics.record_timing("api_response_time", duration, {"endpoint": "batch_quotes", "version": "v2"})
        monitoring_service.metrics.record_counter("api_requests_success", 1, {"endpoint": "batch_quotes", "version": "v2"})
        
        return jsonify({
            "version": "2.0",
            "successful_quotes": results,
            "failed_symbols": errors,
            "total_requested": len(symbols),
            "successful_count": len(results),
            "failed_count": len(errors),
            "timestamp": datetime.now().isoformat(),
            "processing_time_ms": round((duration * 1000), 2)
        })
        
    except Exception as e:
        duration = time.time() - start_time
        monitoring_service.metrics.record_timing("api_response_time", duration, {"endpoint": "batch_quotes", "version": "v2", "status": "error"})
        monitoring_service.metrics.record_counter("api_requests_error", 1, {"endpoint": "batch_quotes", "version": "v2"})
        
        logger.error(f"Batch quotes request failed: {e}")
        return jsonify({
            "version": "2.0",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@api_v2.route("/websocket/fallback/<string:symbol>")
def websocket_fallback_v2(symbol):
    """Fallback HTTP endpoint for WebSocket failures."""
    try:
        # This endpoint provides the same data that would be sent via WebSocket
        stock_quote = None
        if cache_integration:
            stock_quote = cache_integration.get_stock_data(symbol, fetch_if_missing=False)
        
        if stock_quote:
            return jsonify({
                "version": "2.0",
                "type": "stock_update",
                "symbol": symbol,
                "data": {
                    "current_price": stock_quote.current_price,
                    "change": stock_quote.change,
                    "percent_change": stock_quote.percent_change,
                    "volume": stock_quote.volume,
                    "timestamp": stock_quote.timestamp.isoformat()
                },
                "fallback": True,
                "message": "WebSocket unavailable, using HTTP fallback"
            })
        else:
            return jsonify({
                "version": "2.0",
                "error": "No cached data available",
                "symbol": symbol,
                "fallback": True,
                "timestamp": datetime.now().isoformat()
            }), 404
            
    except Exception as e:
        return jsonify({
            "version": "2.0",
            "error": str(e),
            "symbol": symbol,
            "fallback": True,
            "timestamp": datetime.now().isoformat()
        }), 500

@api_v2.route("/cache/status")
def cache_status_v2():
    """Get cache status and performance metrics."""
    try:
        if not cache_integration:
            return jsonify({
                "version": "2.0",
                "error": "Cache integration not available",
                "timestamp": datetime.now().isoformat()
            }), 503
        
        performance_stats = cache_integration.get_performance_stats()
        cache_status = cache_integration.get_cache_status()
        
        return jsonify({
            "version": "2.0",
            "performance": performance_stats,
            "cache_info": cache_status,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            "version": "2.0",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route("/api/websocket/stats")
def websocket_stats():
    """Get WebSocket connection statistics."""
    try:
        stats = websocket_manager.get_connection_stats()
        monitoring_service.metrics.record_gauge("websocket_connections", stats["connected_clients"])
        return jsonify(stats)
    except Exception as e:
        error_handler.record_error("websocket", e)
        return jsonify({"error": str(e)}), 500

# Health check endpoints
@app.route("/health")
def health_check():
    """Basic health check endpoint."""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "bse-data-optimization"
    })

@app.route("/health/detailed")
def detailed_health_check():
    """Detailed health check with all service statuses."""
    try:
        system_status = monitoring_service.get_system_status()
        return jsonify(system_status)
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route("/health/services")
def service_health():
    """Get health status of all registered services."""
    try:
        service_status = error_handler.get_all_service_status()
        return jsonify({
            "services": service_status,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Monitoring endpoints
@app.route("/metrics")
def get_metrics():
    """Get system metrics."""
    try:
        metrics = monitoring_service.metrics.get_all_metrics()
        return jsonify({
            "metrics": metrics,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/metrics/<metric_name>")
def get_metric_summary(metric_name):
    """Get summary for a specific metric."""
    try:
        time_window = request.args.get('window', '5m')
        
        # Parse time window
        if time_window.endswith('m'):
            minutes = int(time_window[:-1])
            from datetime import timedelta
            window = timedelta(minutes=minutes)
        elif time_window.endswith('h'):
            hours = int(time_window[:-1])
            from datetime import timedelta
            window = timedelta(hours=hours)
        else:
            window = None
        
        summary = monitoring_service.metrics.get_metric_summary(metric_name, window)
        return jsonify(summary)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/alerts")
def get_alerts():
    """Get active alerts."""
    try:
        alerts = monitoring_service.get_active_alerts()
        return jsonify({
            "alerts": alerts,
            "count": len(alerts),
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/alerts/<alert_id>/resolve", methods=["POST"])
def resolve_alert(alert_id):
    """Resolve an alert."""
    try:
        success = monitoring_service.resolve_alert(alert_id)
        if success:
            return jsonify({
                "message": f"Alert {alert_id} resolved",
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({"error": "Alert not found or already resolved"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/circuit-breakers")
def get_circuit_breakers():
    """Get circuit breaker states."""
    try:
        breakers = {
            name: breaker.get_state()
            for name, breaker in monitoring_service.circuit_breakers.items()
        }
        return jsonify({
            "circuit_breakers": breakers,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Add health checks
def check_bse_api():
    """Health check for BSE API."""
    try:
        # Try to get a simple quote to test API connectivity
        test_quote = b.getQuote("500325")  # Reliance stock
        return test_quote is not None
    except Exception:
        return False

def check_cache():
    """Health check for Redis cache."""
    if cache_manager is None:
        return False
    try:
        return cache_manager.ping()
    except Exception:
        return False

def check_websocket():
    """Health check for WebSocket service."""
    try:
        stats = websocket_manager.get_connection_stats()
        return True
    except Exception:
        return False

# Enhanced WebSocket event handlers
@socketio.on('subscribe_batch')
def handle_batch_subscribe(data):
    """Handle batch subscription to multiple symbols."""
    from flask_socketio import emit
    try:
        client_id = request.sid
        symbols = data.get('symbols', [])
        
        if not isinstance(symbols, list):
            emit('error', {'message': 'Symbols must be a list'})
            return
        
        if len(symbols) > 100:  # Limit subscriptions per client
            emit('error', {'message': 'Maximum 100 symbols allowed per client'})
            return
        
        # Subscribe to symbols
        websocket_manager.handle_client_subscription(client_id, symbols)
        
        # Send current data for subscribed symbols if available
        if cache_integration:
            current_data = {}
            for symbol in symbols:
                stock_quote = cache_integration.get_stock_data(symbol, fetch_if_missing=False)
                if stock_quote:
                    current_data[symbol] = {
                        "current_price": stock_quote.current_price,
                        "change": stock_quote.change,
                        "percent_change": stock_quote.percent_change,
                        "timestamp": stock_quote.timestamp.isoformat()
                    }
            
            if current_data:
                emit('batch_data', {
                    'type': 'initial_data',
                    'data': current_data,
                    'timestamp': datetime.now().isoformat()
                })
        
        logger.info(f"Client {client_id} subscribed to {len(symbols)} symbols via batch")
        
    except Exception as e:
        logger.error(f"Error in batch subscribe: {e}")
        emit('error', {'message': str(e)})

@socketio.on('get_connection_info')
def handle_connection_info():
    """Provide connection information to client."""
    from flask_socketio import emit
    try:
        client_id = request.sid
        subscriptions = websocket_manager.client_subscriptions.get(client_id, set())
        
        emit('connection_info', {
            'client_id': client_id,
            'subscribed_symbols': list(subscriptions),
            'subscription_count': len(subscriptions),
            'server_time': datetime.now().isoformat(),
            'cache_enabled': cache_integration is not None
        })
        
    except Exception as e:
        logger.error(f"Error getting connection info: {e}")
        emit('error', {'message': str(e)})

@socketio.on('request_symbol_data')
def handle_symbol_data_request(data):
    """Handle request for specific symbol data."""
    from flask_socketio import emit
    try:
        symbol = data.get('symbol')
        if not symbol:
            emit('error', {'message': 'Symbol is required'})
            return
        
        if cache_integration:
            stock_quote = cache_integration.get_stock_data(symbol, fetch_if_missing=True)
            if stock_quote:
                emit('symbol_data', {
                    'symbol': symbol,
                    'data': {
                        "current_price": stock_quote.current_price,
                        "change": stock_quote.change,
                        "percent_change": stock_quote.percent_change,
                        "volume": stock_quote.volume,
                        "timestamp": stock_quote.timestamp.isoformat(),
                        "company_name": stock_quote.company_name
                    },
                    'timestamp': datetime.now().isoformat()
                })
            else:
                emit('error', {'message': f'No data available for symbol {symbol}'})
        else:
            emit('error', {'message': 'Cache integration not available'})
            
    except Exception as e:
        logger.error(f"Error handling symbol data request: {e}")
        emit('error', {'message': str(e)})

@socketio.on('place_order')
def handle_place_order(data):
    """Handle order placement from client."""
    from flask_socketio import emit
    from flask import request
    try:
        client_id = request.sid
        logger.info(f"Received order from client {client_id}: {data}")
        
        # Here you would typically process the order
        # For now, just acknowledge it
        
        emit('order_update', {
            'status': 'received',
            'order_id': data.get('id'),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error handling place_order: {e}")
        emit('error', {'message': str(e)})

@app.route('/api/historical-data/<string:symbol>/<string:timeframe>')
def get_historical_data(symbol, timeframe):
    """Get historical data for a stock."""
    import random
    from datetime import datetime, timedelta

    now = datetime.now()
    data = []
    if timeframe == '1d':
        for i in range(24):
            data.append({
                'time': (now - timedelta(hours=i)).strftime('%H:%M'),
                'price': 100 + random.uniform(-5, 5)
            })
    elif timeframe == '5d':
        for i in range(5 * 24):
            data.append({
                'time': (now - timedelta(hours=i)).strftime('%Y-%m-%d %H:%M'),
                'price': 100 + random.uniform(-10, 10)
            })
    else:
        for i in range(30):
            data.append({
                'time': (now - timedelta(days=i)).strftime('%Y-%m-%d'),
                'price': 100 + random.uniform(-20, 20)
            })
    data.reverse()
    return jsonify(data)

# Register health checks
monitoring_service.add_health_check("bse_api", check_bse_api, "BSE API connectivity")
monitoring_service.add_health_check("cache", check_cache, "Redis cache connectivity")
monitoring_service.add_health_check("websocket", check_websocket, "WebSocket service")

# Register API blueprints
app.register_blueprint(legacy_api)
app.register_blueprint(api_v1)
app.register_blueprint(api_v2)

# Add API version discovery endpoint
@app.route("/api/versions")
def api_versions():
    """Get available API versions."""
    return jsonify({
        "available_versions": ["1.0", "2.0"],
        "current_version": "2.0",
        "legacy_support": True,
        "endpoints": {
            "v1": {
                "base_url": "/api/v1",
                "features": ["basic_quotes", "stock_list", "caching"]
            },
            "v2": {
                "base_url": "/api/v2", 
                "features": ["enhanced_quotes", "batch_quotes", "websocket_fallback", "cache_status"]
            },
            "legacy": {
                "base_url": "/api",
                "features": ["backward_compatibility"],
                "deprecated": True
            }
        },
        "timestamp": datetime.now().isoformat()
    })

if __name__ == "__main__":
    # Start cache integration if available
    if cache_integration:
        # Add essential stocks for cache warming
        essential_stocks = ["500325", "500209", "532540", "500180", "500696"]  # Popular stocks
        for stock in essential_stocks:
            cache_integration.add_essential_stock(stock)
        
        # Start periodic cache warming
        cache_integration.start_periodic_cache_warming(interval=300)  # 5 minutes
    
    # Start monitoring service
    monitoring_service.start_monitoring(check_interval=30)
    
    logger.info("Starting BSE Data Optimization Server with monitoring enabled")
    logger.info(f"API versions available: /api (legacy), /api/v1, /api/v2")
    
    try:
        # Use socketio.run instead of app.run for WebSocket support
        socketio.run(app, host='0.0.0.0', port=3002, debug=True)
    finally:
        # Stop services on shutdown
        if cache_integration:
            cache_integration.stop()
        monitoring_service.stop_monitoring()
