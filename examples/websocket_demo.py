# examples/websocket_demo.py
"""
Demo script showing WebSocket functionality for real-time stock updates.
This demonstrates how the WebSocketManager can be used to broadcast stock updates.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from flask_socketio import SocketIO
from services.websocket_manager import WebSocketManager
import time
import threading
import random

def create_demo_app():
    """Create a demo Flask app with WebSocket support."""
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'demo-secret-key'
    
    # Initialize SocketIO
    socketio = SocketIO(app, cors_allowed_origins="*")
    
    # Initialize WebSocket manager
    websocket_manager = WebSocketManager(socketio)
    
    @app.route('/')
    def index():
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>WebSocket Demo</title>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
        </head>
        <body>
            <h1>BSE WebSocket Demo</h1>
            <div id="status">Connecting...</div>
            <div id="subscriptions">
                <h3>Subscribe to Stocks:</h3>
                <button onclick="subscribe(['RELIANCE', 'TCS', 'INFY'])">Subscribe to RELIANCE, TCS, INFY</button>
                <button onclick="subscribe(['HDFC', 'ICICIBANK'])">Subscribe to HDFC, ICICIBANK</button>
            </div>
            <div id="updates">
                <h3>Real-time Updates:</h3>
                <div id="messages"></div>
            </div>
            
            <script>
                const socket = io();
                
                socket.on('connect', function() {
                    document.getElementById('status').innerHTML = 'Connected to WebSocket server';
                });
                
                socket.on('connection_established', function(data) {
                    console.log('Connection established:', data);
                    addMessage('Connected with client ID: ' + data.client_id);
                });
                
                socket.on('message', function(data) {
                    if (data.type === 'subscription_confirmed') {
                        addMessage('Subscribed to: ' + data.symbols.join(', '));
                    }
                });
                
                socket.on('stock_update', function(data) {
                    addMessage('Stock Update - ' + data.symbol + ': $' + data.data.price + 
                              ' (Change: ' + data.data.change + ')');
                });
                
                socket.on('system_message', function(data) {
                    addMessage('System: ' + JSON.stringify(data.data));
                });
                
                function subscribe(symbols) {
                    socket.emit('subscribe', {symbols: symbols});
                }
                
                function addMessage(message) {
                    const div = document.createElement('div');
                    div.innerHTML = new Date().toLocaleTimeString() + ' - ' + message;
                    document.getElementById('messages').appendChild(div);
                }
            </script>
        </body>
        </html>
        '''
    
    @app.route('/api/stats')
    def stats():
        """Get WebSocket connection statistics."""
        return websocket_manager.get_connection_stats()
    
    return app, socketio, websocket_manager

def simulate_stock_updates(websocket_manager):
    """Simulate real-time stock price updates."""
    stocks = {
        'RELIANCE': {'price': 2500.0, 'base_price': 2500.0},
        'TCS': {'price': 3200.0, 'base_price': 3200.0},
        'INFY': {'price': 1450.0, 'base_price': 1450.0},
        'HDFC': {'price': 1600.0, 'base_price': 1600.0},
        'ICICIBANK': {'price': 950.0, 'base_price': 950.0}
    }
    
    print("Starting stock price simulation...")
    
    while True:
        # Pick a random stock to update
        symbol = random.choice(list(stocks.keys()))
        stock = stocks[symbol]
        
        # Generate random price change (±2%)
        change_percent = random.uniform(-0.02, 0.02)
        new_price = stock['base_price'] * (1 + change_percent)
        price_change = new_price - stock['price']
        
        stock['price'] = new_price
        
        # Create stock update data
        stock_data = {
            'price': round(new_price, 2),
            'change': round(price_change, 2),
            'pChange': round((price_change / stock['price']) * 100, 2),
            'volume': random.randint(1000, 10000)
        }
        
        # Broadcast update
        websocket_manager.broadcast_stock_update(symbol, stock_data)
        
        print(f"Updated {symbol}: ${stock_data['price']} (Change: {stock_data['change']})")
        
        # Wait 2-5 seconds before next update
        time.sleep(random.uniform(2, 5))

if __name__ == '__main__':
    app, socketio, websocket_manager = create_demo_app()
    
    # Start stock price simulation in background thread
    simulation_thread = threading.Thread(
        target=simulate_stock_updates, 
        args=(websocket_manager,),
        daemon=True
    )
    simulation_thread.start()
    
    print("Starting WebSocket demo server...")
    print("Open http://localhost:5001 in your browser to see the demo")
    print("Press Ctrl+C to stop")
    
    try:
        socketio.run(app, host='0.0.0.0', port=5001, debug=False)
    except KeyboardInterrupt:
        print("\nShutting down demo server...")