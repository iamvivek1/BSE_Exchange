# services/websocket_manager.py
from typing import Dict, List, Set, Optional, Callable
from flask_socketio import SocketIO, emit, disconnect
import logging
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class WebSocketManager:
    """
    Manages WebSocket connections for real-time stock data updates.
    Handles client subscriptions, message broadcasting, and connection lifecycle.
    """
    
    def __init__(self, socketio: SocketIO):
        self.socketio = socketio
        self.client_subscriptions: Dict[str, Set[str]] = {}  # client_id -> set of symbols
        self.symbol_subscribers: Dict[str, Set[str]] = {}    # symbol -> set of client_ids
        self.connected_clients: Set[str] = set()
        self.message_queue: Dict[str, List[dict]] = {}       # client_id -> queued messages
        
        # Register SocketIO event handlers
        self._register_event_handlers()
    
    def _register_event_handlers(self):
        """Register SocketIO event handlers for client connections and messages."""
        
        @self.socketio.on('connect')
        def handle_connect():
            client_id = self._get_client_id()
            self.connected_clients.add(client_id)
            self.client_subscriptions[client_id] = set()
            logger.info(f"Client {client_id} connected")
            
            # Send any queued messages
            self._send_queued_messages(client_id)
            
            emit('connection_established', {
                'client_id': client_id,
                'timestamp': datetime.now().isoformat()
            })
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            client_id = self._get_client_id()
            self._cleanup_client(client_id)
            logger.info(f"Client {client_id} disconnected")
        
        @self.socketio.on('subscribe')
        def handle_subscribe(data):
            client_id = self._get_client_id()
            symbols = data.get('symbols', [])
            self.handle_client_subscription(client_id, symbols)
        
        @self.socketio.on('unsubscribe')
        def handle_unsubscribe(data):
            client_id = self._get_client_id()
            symbols = data.get('symbols', [])
            self._unsubscribe_client_from_symbols(client_id, symbols)
        
        @self.socketio.on('ping')
        def handle_ping():
            emit('pong', {'timestamp': datetime.now().isoformat()})
        
        # Store references to handlers for testing
        self._connect_handler = handle_connect
        self._disconnect_handler = handle_disconnect
        self._subscribe_handler = handle_subscribe
        self._unsubscribe_handler = handle_unsubscribe
        self._ping_handler = handle_ping
    
    def _get_client_id(self) -> str:
        """Get the current client's session ID."""
        from flask import request
        return request.sid
    
    def handle_client_subscription(self, client_id: str, symbols: List[str]):
        """
        Handle client subscription to specific stock symbols.
        
        Args:
            client_id: Unique identifier for the client
            symbols: List of stock symbols to subscribe to
        """
        if client_id not in self.connected_clients:
            logger.warning(f"Subscription request from disconnected client {client_id}")
            return
        
        # Add symbols to client's subscription list
        if client_id not in self.client_subscriptions:
            self.client_subscriptions[client_id] = set()
        
        new_symbols = set(symbols) - self.client_subscriptions[client_id]
        self.client_subscriptions[client_id].update(symbols)
        
        # Update reverse mapping (symbol -> clients)
        for symbol in new_symbols:
            if symbol not in self.symbol_subscribers:
                self.symbol_subscribers[symbol] = set()
            self.symbol_subscribers[symbol].add(client_id)
        
        logger.info(f"Client {client_id} subscribed to {len(new_symbols)} new symbols: {new_symbols}")
        
        # Confirm subscription
        self.send_to_client(client_id, {
            'type': 'subscription_confirmed',
            'symbols': list(symbols),
            'timestamp': datetime.now().isoformat()
        })
    
    def _unsubscribe_client_from_symbols(self, client_id: str, symbols: List[str]):
        """Remove client subscription from specific symbols."""
        if client_id not in self.client_subscriptions:
            return
        
        for symbol in symbols:
            # Remove from client's subscriptions
            self.client_subscriptions[client_id].discard(symbol)
            
            # Remove from symbol's subscribers
            if symbol in self.symbol_subscribers:
                self.symbol_subscribers[symbol].discard(client_id)
                # Clean up empty symbol entries
                if not self.symbol_subscribers[symbol]:
                    del self.symbol_subscribers[symbol]
        
        logger.info(f"Client {client_id} unsubscribed from symbols: {symbols}")
    
    def broadcast_stock_update(self, symbol: str, data: dict):
        """
        Broadcast stock update to all clients subscribed to the symbol.
        
        Args:
            symbol: Stock symbol that was updated
            data: Stock data to broadcast
        """
        if symbol not in self.symbol_subscribers:
            return
        
        message = {
            'type': 'stock_update',
            'symbol': symbol,
            'data': data,
            'timestamp': datetime.now().isoformat()
        }
        
        subscribers = self.symbol_subscribers[symbol].copy()
        disconnected_clients = []
        
        for client_id in subscribers:
            if client_id in self.connected_clients:
                try:
                    self.socketio.emit('stock_update', message, room=client_id)
                except Exception as e:
                    logger.error(f"Failed to send update to client {client_id}: {e}")
                    disconnected_clients.append(client_id)
            else:
                # Queue message for disconnected client
                self._queue_message_for_client(client_id, message)
                disconnected_clients.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected_clients:
            if client_id not in self.connected_clients:
                self._cleanup_client(client_id)
        
        logger.debug(f"Broadcasted update for {symbol} to {len(subscribers)} clients")
    
    def send_to_client(self, client_id: str, message: dict):
        """
        Send a message to a specific client.
        
        Args:
            client_id: Target client identifier
            message: Message to send
        """
        if client_id in self.connected_clients:
            try:
                self.socketio.emit('message', message, room=client_id)
            except Exception as e:
                logger.error(f"Failed to send message to client {client_id}: {e}")
        else:
            # Queue message for when client reconnects
            self._queue_message_for_client(client_id, message)
    
    def _queue_message_for_client(self, client_id: str, message: dict):
        """Queue a message for a disconnected client."""
        if client_id not in self.message_queue:
            self.message_queue[client_id] = []
        
        # Limit queue size to prevent memory issues
        max_queue_size = 100
        if len(self.message_queue[client_id]) >= max_queue_size:
            self.message_queue[client_id].pop(0)  # Remove oldest message
        
        self.message_queue[client_id].append(message)
    
    def _send_queued_messages(self, client_id: str):
        """Send any queued messages to a reconnected client."""
        if client_id in self.message_queue:
            messages = self.message_queue[client_id]
            for message in messages:
                try:
                    self.socketio.emit('queued_message', message, room=client_id)
                except Exception as e:
                    logger.error(f"Failed to send queued message to client {client_id}: {e}")
            
            # Clear the queue
            del self.message_queue[client_id]
            logger.info(f"Sent {len(messages)} queued messages to client {client_id}")
    
    def _cleanup_client(self, client_id: str):
        """Clean up all data associated with a disconnected client."""
        # Remove from connected clients
        self.connected_clients.discard(client_id)
        
        # Remove client subscriptions
        if client_id in self.client_subscriptions:
            subscribed_symbols = self.client_subscriptions[client_id]
            for symbol in subscribed_symbols:
                if symbol in self.symbol_subscribers:
                    self.symbol_subscribers[symbol].discard(client_id)
                    # Clean up empty symbol entries
                    if not self.symbol_subscribers[symbol]:
                        del self.symbol_subscribers[symbol]
            
            del self.client_subscriptions[client_id]
        
        # Keep message queue for potential reconnection (will be cleaned up later)
        logger.info(f"Cleaned up client {client_id}")
    
    def get_connection_stats(self) -> dict:
        """Get current connection statistics."""
        return {
            'connected_clients': len(self.connected_clients),
            'total_subscriptions': sum(len(subs) for subs in self.client_subscriptions.values()),
            'active_symbols': len(self.symbol_subscribers),
            'queued_messages': sum(len(queue) for queue in self.message_queue.values())
        }
    
    def broadcast_system_message(self, message: dict):
        """Broadcast a system message to all connected clients."""
        system_message = {
            'type': 'system_message',
            'data': message,
            'timestamp': datetime.now().isoformat()
        }
        
        for client_id in self.connected_clients.copy():
            try:
                self.socketio.emit('system_message', system_message, room=client_id)
            except Exception as e:
                logger.error(f"Failed to send system message to client {client_id}: {e}")