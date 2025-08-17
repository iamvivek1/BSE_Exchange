# BSE Frontend WebSocket Implementation

## Overview

This document describes the enhanced frontend WebSocket implementation for real-time BSE stock data communication. The implementation provides automatic reconnection, client-side caching, performance monitoring, and comprehensive error handling.

## Features

### 🔄 Real-time Communication
- **WebSocket Connection**: Persistent connection for real-time stock updates
- **Automatic Reconnection**: Exponential backoff strategy with configurable retry limits
- **Message Queuing**: Queues messages when disconnected and flushes on reconnection
- **Heartbeat Mechanism**: Keeps connection alive with periodic ping/pong

### 📊 Stock Data Management
- **Real-time Updates**: Sub-second stock price updates via WebSocket
- **Client-side Caching**: 5-second cache with automatic expiration
- **Subscription Management**: Subscribe/unsubscribe to specific stock symbols
- **Fallback HTTP**: Automatic fallback to REST API when WebSocket unavailable

### 📈 Order Management
- **Real-time Orders**: Place orders via WebSocket with immediate feedback
- **Order Status Updates**: Real-time order status changes (pending, filled, cancelled)
- **Optimistic Updates**: Immediate UI updates with server confirmation
- **Error Handling**: Graceful handling of order placement failures

### 🎯 Performance Optimization
- **Connection Monitoring**: Track connection time, latency, and error rates
- **Quality Indicators**: Visual connection quality feedback
- **Memory Management**: Efficient cache management to prevent memory leaks
- **Bandwidth Optimization**: Delta updates and message compression ready

## Architecture

### WebSocket Manager Class

```javascript
class WebSocketManager {
  // Connection management
  connect()           // Establish WebSocket connection
  disconnect()        // Close connection gracefully
  send(message)       // Send message with queuing support
  
  // Subscription management
  subscribe(symbol)   // Subscribe to stock updates
  unsubscribe(symbol) // Unsubscribe from stock updates
  
  // Data management
  updateCache(symbol, data)  // Update client-side cache
  getCachedData(symbol)      // Retrieve cached data
  
  // Event handlers
  onConnected()       // Connection established callback
  onDisconnected()    // Connection lost callback
  onStockUpdate()     // Stock data update callback
  onOrderUpdate()     // Order status update callback
}
```

### Message Protocol

#### Outgoing Messages (Client → Server)

```javascript
// Subscribe to stock updates
{
  "type": "subscribe",
  "symbol": "500325"
}

// Place order
{
  "type": "place_order",
  "data": {
    "id": "ORD-ABC123",
    "symbol": "500325",
    "side": "buy",
    "price": 2500.00,
    "amount": 10
  }
}

// Heartbeat
{
  "type": "ping"
}
```

#### Incoming Messages (Server → Client)

```javascript
// Stock price update
{
  "type": "stock_update",
  "data": {
    "symbol": "500325",
    "price": 2501.50,
    "change": 1.50,
    "percent_change": 0.06,
    "company_name": "RELIANCE INDUSTRIES LTD.",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}

// Order status update
{
  "type": "order_update",
  "data": {
    "id": "ORD-ABC123",
    "status": "filled",
    "timestamp": "2024-01-15T10:30:05Z"
  }
}

// Market status
{
  "type": "market_status",
  "data": {
    "status": "open",
    "timestamp": "2024-01-15T09:15:00Z"
  }
}
```

## Implementation Details

### Connection Management

```javascript
// Exponential backoff for reconnection
const delay = Math.min(
  this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1),
  this.maxReconnectDelay
);

// Connection status indicators
this.updateConnectionStatus(connected);
this.updateConnectionQuality();
```

### Client-side Caching

```javascript
// Cache with TTL
updateCache(symbol, data) {
  this.cache.set(symbol, {
    data: data,
    timestamp: Date.now()
  });
}

// Cache retrieval with expiration
getCachedData(symbol) {
  const cached = this.cache.get(symbol);
  if (cached && (Date.now() - cached.timestamp) < this.cacheTimeout) {
    return cached.data;
  }
  return null;
}
```

### Performance Monitoring

```javascript
class PerformanceMonitor {
  recordConnectionTime()     // Track connection establishment time
  recordMessageLatency()     // Track message round-trip time
  recordUpdate()            // Track update frequency
  getMetrics()              // Get performance statistics
}
```

## Usage Examples

### Basic Setup

```javascript
// Initialize WebSocket manager
const wsManager = new WebSocketManager();

// Set up event handlers
wsManager.onConnected = () => {
  console.log('Connected to real-time data feed');
};

wsManager.onStockUpdate = (data) => {
  updateStockDisplay(data);
};

// Connect
wsManager.connect();
```

### Stock Subscription

```javascript
// Subscribe to multiple stocks
const watchlist = ['500325', '500112', '500470'];
watchlist.forEach(symbol => {
  wsManager.subscribe(symbol);
});

// Handle real-time updates
function updateStockDisplay(data) {
  const element = document.getElementById(`stock-${data.symbol}`);
  element.querySelector('.price').textContent = `₹${data.price}`;
  element.querySelector('.change').textContent = `${data.percent_change}%`;
}
```

### Order Placement

```javascript
// Place order with real-time feedback
async function placeOrder(side, price, amount) {
  const orderData = {
    id: generateOrderId(),
    symbol: selected.symbol,
    side: side,
    price: price,
    amount: amount
  };

  // Send via WebSocket
  wsManager.send({
    type: 'place_order',
    data: orderData
  });

  // Update UI optimistically
  addOrderToUI(orderData, 'pending');
}
```

## Testing

### Running Tests

```bash
# Install dependencies
npm install

# Run all tests
npm test

# Run WebSocket-specific tests
npm run test:frontend

# Run tests with coverage
npm run test:coverage
```

### Test Coverage

The test suite covers:
- ✅ Connection establishment and management
- ✅ Automatic reconnection with exponential backoff
- ✅ Message queuing and flushing
- ✅ Stock subscription management
- ✅ Real-time data updates and caching
- ✅ Order placement and status updates
- ✅ Error handling and recovery
- ✅ Performance monitoring
- ✅ Integration workflows

### Manual Testing

Open `tests/test_frontend_websocket.html` in a browser to run interactive tests:

```bash
# Serve the test file
npm run serve
# Navigate to http://localhost:8080/tests/test_frontend_websocket.html
```

## Configuration

### WebSocket Settings

```javascript
const wsManager = new WebSocketManager();

// Reconnection settings
wsManager.maxReconnectAttempts = 10;
wsManager.reconnectDelay = 1000;        // Initial delay: 1 second
wsManager.maxReconnectDelay = 30000;    // Max delay: 30 seconds

// Cache settings
wsManager.cacheTimeout = 5000;          // Cache TTL: 5 seconds

// Heartbeat settings
wsManager.heartbeatInterval = 30000;    // Ping every 30 seconds
```

### Environment Variables

```javascript
// WebSocket URL configuration
const wsUrl = process.env.WS_URL || 'ws://localhost:5000/ws';

// Debug mode
const debugMode = process.env.DEBUG === 'true';
```

## Performance Metrics

The implementation tracks several performance metrics:

- **Connection Time**: Time to establish WebSocket connection
- **Message Latency**: Round-trip time for messages
- **Update Frequency**: Rate of incoming stock updates
- **Error Rate**: Percentage of failed operations
- **Cache Hit Rate**: Efficiency of client-side caching

## Browser Compatibility

- ✅ Chrome 16+
- ✅ Firefox 11+
- ✅ Safari 7+
- ✅ Edge 12+
- ✅ Mobile browsers (iOS Safari, Chrome Mobile)

## Security Considerations

- **Origin Validation**: WebSocket connections validate origin headers
- **Authentication**: Token-based authentication for WebSocket connections
- **Rate Limiting**: Client-side rate limiting to prevent spam
- **Data Validation**: All incoming messages are validated before processing

## Troubleshooting

### Common Issues

1. **Connection Fails**
   - Check WebSocket server is running
   - Verify firewall settings
   - Check browser console for errors

2. **Frequent Disconnections**
   - Check network stability
   - Verify heartbeat mechanism
   - Review server-side connection limits

3. **Missing Updates**
   - Verify subscription status
   - Check message queue
   - Review cache expiration settings

### Debug Mode

Enable debug logging:

```javascript
wsManager.debug = true;
```

This will log all WebSocket events, messages, and state changes to the console.

## Future Enhancements

- 🔄 **Message Compression**: Implement gzip compression for large messages
- 📊 **Advanced Metrics**: Add more detailed performance analytics
- 🔐 **Enhanced Security**: Implement message encryption
- 📱 **Mobile Optimization**: Optimize for mobile network conditions
- 🎯 **Smart Reconnection**: Implement intelligent reconnection based on network conditions

## Requirements Fulfilled

This implementation satisfies the following requirements:

- **Requirement 1.1**: Real-time stock price updates with minimal latency ✅
- **Requirement 1.2**: Sub-second update frequencies for multiple stocks ✅
- **Requirement 4.4**: Bidirectional real-time communication for orders ✅

The WebSocket implementation provides a robust, scalable foundation for real-time trading applications with comprehensive error handling, performance monitoring, and user experience optimizations.