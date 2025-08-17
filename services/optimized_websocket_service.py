# services/optimized_websocket_service.py
from typing import Dict, List, Any, Optional, Union
from flask_socketio import SocketIO, emit
import logging
from datetime import datetime
import json
import base64

from services.compression_service import CompressionService
from services.websocket_manager import WebSocketManager
from models.stock_quote import StockQuote

logger = logging.getLogger(__name__)

class OptimizedWebSocketService:
    """
    Enhanced WebSocket service with data compression and bandwidth optimization
    for high-frequency stock data updates.
    """
    
    def __init__(self, socketio: SocketIO, compression_service: Optional[CompressionService] = None):
        self.socketio = socketio
        self.compression_service = compression_service or CompressionService()
        self.websocket_manager = WebSocketManager(socketio)
        
        # Client capabilities tracking
        self.client_capabilities: Dict[str, Dict] = {}  # client_id -> capabilities
        
        # Batch update configuration
        self.batch_config = {
            'max_batch_size': 10,
            'batch_timeout_ms': 100,
            'enable_compression': True,
            'compression_threshold': 500  # bytes
        }
        
        # Pending batch updates
        self.pending_batches: Dict[str, List[Dict]] = {}  # client_id -> pending updates
        
        self._register_enhanced_handlers()
    
    def _register_enhanced_handlers(self):
        """Register enhanced WebSocket event handlers with compression support."""
        
        @self.socketio.on('client_capabilities')
        def handle_client_capabilities(data):
            """Handle client capability negotiation."""
            client_id = self._get_client_id()
            capabilities = {
                'supports_compression': data.get('supports_compression', False),
                'supports_delta_updates': data.get('supports_delta_updates', False),
                'supports_batch_updates': data.get('supports_batch_updates', False),
                'max_message_size': data.get('max_message_size', 64 * 1024),  # 64KB default
                'preferred_compression': data.get('preferred_compression', 'msgpack')
            }
            
            self.client_capabilities[client_id] = capabilities
            logger.info(f"Client {client_id} capabilities: {capabilities}")
            
            # Send server capabilities
            emit('server_capabilities', {
                'supports_compression': True,
                'supports_delta_updates': True,
                'supports_batch_updates': True,
                'compression_methods': ['msgpack', 'gzip'],
                'max_batch_size': self.batch_config['max_batch_size']
            })
        
        @self.socketio.on('request_compression_stats')
        def handle_compression_stats_request():
            """Send compression statistics to client."""
            stats = self.compression_service.get_compression_stats()
            emit('compression_stats', stats)
        
        # Store handler references for testing
        self._capabilities_handler = handle_client_capabilities
        self._stats_handler = handle_compression_stats_request
    
    def handle_client_capabilities_direct(self, data: Dict, client_id: str = None):
        """Direct method for handling client capabilities (for testing)."""
        if client_id is None:
            client_id = self._get_client_id()
            
        capabilities = {
            'supports_compression': data.get('supports_compression', False),
            'supports_delta_updates': data.get('supports_delta_updates', False),
            'supports_batch_updates': data.get('supports_batch_updates', False),
            'max_message_size': data.get('max_message_size', 64 * 1024),
            'preferred_compression': data.get('preferred_compression', 'msgpack')
        }
        
        self.client_capabilities[client_id] = capabilities
        logger.info(f"Client {client_id} capabilities: {capabilities}")
        
        return capabilities
    
    def handle_compression_stats_request_direct(self):
        """Direct method for handling compression stats request (for testing)."""
        stats = self.compression_service.get_compression_stats()
        self.socketio.emit('compression_stats', stats)
        return stats
    
    def _get_client_id(self) -> str:
        """Get the current client's session ID."""
        from flask import request
        return request.sid
    
    def send_optimized_stock_update(self, symbol: str, stock_data: Union[StockQuote, Dict], 
                                  force_full_update: bool = False):
        """
        Send optimized stock update to subscribed clients with compression and delta updates.
        
        Args:
            symbol: Stock symbol
            stock_data: Stock data to send
            force_full_update: Force sending full update instead of delta
        """
        if symbol not in self.websocket_manager.symbol_subscribers:
            return
        
        subscribers = self.websocket_manager.symbol_subscribers[symbol].copy()
        
        for client_id in subscribers:
            if client_id not in self.websocket_manager.connected_clients:
                continue
            
            try:
                self._send_update_to_client(client_id, symbol, stock_data, force_full_update)
            except Exception as e:
                logger.error(f"Failed to send optimized update to client {client_id}: {e}")
    
    def _send_update_to_client(self, client_id: str, symbol: str, 
                              stock_data: Union[StockQuote, Dict], force_full_update: bool):
        """Send update to a specific client with appropriate optimization."""
        
        client_caps = self.client_capabilities.get(client_id, {})
        supports_delta = client_caps.get('supports_delta_updates', False)
        supports_compression = client_caps.get('supports_compression', False)
        supports_batch = client_caps.get('supports_batch_updates', False)
        
        # Create update message
        if supports_delta and not force_full_update:
            update_data = self.compression_service.create_delta_update(symbol, stock_data)
        else:
            update_data = self.compression_service.create_full_update(symbol, stock_data)
        
        # Handle batching if supported
        if supports_batch:
            self._add_to_batch(client_id, update_data)
        else:
            self._send_single_update(client_id, update_data, supports_compression)
    
    def _add_to_batch(self, client_id: str, update_data: Dict):
        """Add update to client's pending batch."""
        if client_id not in self.pending_batches:
            self.pending_batches[client_id] = []
        
        self.pending_batches[client_id].append(update_data)
        
        # Send batch if it reaches max size
        if len(self.pending_batches[client_id]) >= self.batch_config['max_batch_size']:
            self._flush_batch(client_id)
    
    def _send_single_update(self, client_id: str, update_data: Dict, use_compression: bool):
        """Send a single update to client with optional compression."""
        
        message = {
            'type': 'stock_update_optimized',
            'data': update_data,
            'timestamp': datetime.now().isoformat(),
            'compressed': False
        }
        
        # Apply compression if supported and beneficial
        if use_compression and self.batch_config['enable_compression']:
            try:
                # Serialize message to check size
                serialized = json.dumps(message).encode('utf-8')
                
                if len(serialized) > self.batch_config['compression_threshold']:
                    # Compress the update data
                    compressed_data = self.compression_service.compress_stock_data(update_data)
                    
                    # Encode as base64 for JSON transport
                    encoded_data = base64.b64encode(compressed_data).decode('utf-8')
                    
                    message = {
                        'type': 'stock_update_compressed',
                        'data': encoded_data,
                        'timestamp': datetime.now().isoformat(),
                        'compressed': True,
                        'compression_method': 'msgpack'
                    }
            except Exception as e:
                logger.warning(f"Compression failed for client {client_id}: {e}")
        
        # Send the message
        self.socketio.emit('optimized_update', message, room=client_id)
    
    def _flush_batch(self, client_id: str):
        """Flush pending batch updates for a client."""
        if client_id not in self.pending_batches or not self.pending_batches[client_id]:
            return
        
        batch_updates = self.pending_batches[client_id]
        self.pending_batches[client_id] = []
        
        client_caps = self.client_capabilities.get(client_id, {})
        supports_compression = client_caps.get('supports_compression', False)
        
        try:
            if supports_compression and self.batch_config['enable_compression']:
                # Compress entire batch
                compressed_batch = self.compression_service.compress_batch_updates(batch_updates)
                encoded_batch = base64.b64encode(compressed_batch).decode('utf-8')
                
                message = {
                    'type': 'batch_update_compressed',
                    'data': encoded_batch,
                    'count': len(batch_updates),
                    'timestamp': datetime.now().isoformat(),
                    'compressed': True,
                    'compression_method': 'msgpack_gzip'
                }
            else:
                # Send uncompressed batch
                message = {
                    'type': 'batch_update',
                    'data': batch_updates,
                    'count': len(batch_updates),
                    'timestamp': datetime.now().isoformat(),
                    'compressed': False
                }
            
            self.socketio.emit('batch_update', message, room=client_id)
            logger.debug(f"Sent batch of {len(batch_updates)} updates to client {client_id}")
            
        except Exception as e:
            logger.error(f"Failed to send batch to client {client_id}: {e}")
    
    def flush_all_batches(self):
        """Flush all pending batch updates."""
        for client_id in list(self.pending_batches.keys()):
            self._flush_batch(client_id)
    
    def broadcast_optimized_updates(self, updates: List[Dict[str, Any]]):
        """
        Broadcast multiple stock updates efficiently to all relevant clients.
        
        Args:
            updates: List of stock updates, each containing 'symbol' and 'data'
        """
        # Group updates by subscribed clients
        client_updates: Dict[str, List[Dict]] = {}
        
        for update in updates:
            symbol = update['symbol']
            if symbol in self.websocket_manager.symbol_subscribers:
                for client_id in self.websocket_manager.symbol_subscribers[symbol]:
                    if client_id not in client_updates:
                        client_updates[client_id] = []
                    client_updates[client_id].append(update)
        
        # Send optimized updates to each client
        for client_id, client_update_list in client_updates.items():
            if client_id not in self.websocket_manager.connected_clients:
                continue
            
            try:
                self._send_bulk_updates_to_client(client_id, client_update_list)
            except Exception as e:
                logger.error(f"Failed to send bulk updates to client {client_id}: {e}")
    
    def _send_bulk_updates_to_client(self, client_id: str, updates: List[Dict], auto_flush: bool = True):
        """Send multiple updates to a client efficiently."""
        
        client_caps = self.client_capabilities.get(client_id, {})
        supports_batch = client_caps.get('supports_batch_updates', False)
        
        if supports_batch:
            # Add all updates to batch
            for update in updates:
                symbol = update['symbol']
                stock_data = update['data']
                
                if client_caps.get('supports_delta_updates', False):
                    update_data = self.compression_service.create_delta_update(symbol, stock_data)
                else:
                    update_data = self.compression_service.create_full_update(symbol, stock_data)
                
                self._add_to_batch(client_id, update_data)
            
            # Flush the batch if requested
            if auto_flush:
                self._flush_batch(client_id)
        else:
            # Send individual updates
            for update in updates:
                self._send_update_to_client(client_id, update['symbol'], update['data'], False)
    
    def get_optimization_stats(self) -> Dict[str, Any]:
        """Get optimization and performance statistics."""
        compression_stats = self.compression_service.get_compression_stats()
        websocket_stats = self.websocket_manager.get_connection_stats()
        
        return {
            'compression': compression_stats,
            'websocket': websocket_stats,
            'client_capabilities': {
                'total_clients': len(self.client_capabilities),
                'compression_enabled': sum(1 for caps in self.client_capabilities.values() 
                                         if caps.get('supports_compression', False)),
                'delta_enabled': sum(1 for caps in self.client_capabilities.values() 
                                   if caps.get('supports_delta_updates', False)),
                'batch_enabled': sum(1 for caps in self.client_capabilities.values() 
                                   if caps.get('supports_batch_updates', False))
            },
            'pending_batches': {client_id: len(batch) for client_id, batch in self.pending_batches.items()},
            'batch_config': self.batch_config
        }
    
    def update_batch_config(self, config: Dict[str, Any]):
        """Update batch processing configuration."""
        self.batch_config.update(config)
        logger.info(f"Updated batch config: {self.batch_config}")
    
    def cleanup_client_data(self, client_id: str):
        """Clean up optimization data for disconnected client."""
        self.client_capabilities.pop(client_id, None)
        self.pending_batches.pop(client_id, None)
        logger.debug(f"Cleaned up optimization data for client {client_id}")