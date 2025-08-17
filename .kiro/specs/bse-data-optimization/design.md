# Design Document

## Overview

The BSE Data Optimization system will transform the current synchronous, single-request architecture into a high-performance, real-time data delivery system. The design implements a multi-layered caching strategy, WebSocket-based real-time communication, batch processing for BSE API calls, and intelligent data compression to achieve sub-second latency for stock price updates.

## Architecture

### High-Level Architecture

```
┌─────────────────┐    WebSocket    ┌──────────────────┐    Batch API    ┌─────────────┐
│   Frontend      │◄──────────────►│   Backend        │◄──────────────►│   BSE API   │
│   (React/JS)    │                 │   (Flask+Redis)  │                 │             │
└─────────────────┘                 └──────────────────┘                 └─────────────┘
                                             │
                                             ▼
                                    ┌──────────────────┐
                                    │   Redis Cache    │
                                    │   + Pub/Sub      │
                                    └──────────────────┘
```

### Data Flow Architecture

1. **Batch Data Fetcher**: Periodically fetches multiple stock quotes in batches
2. **Cache Layer**: Redis-based caching with TTL and pub/sub for real-time updates
3. **WebSocket Manager**: Handles client connections and broadcasts updates
4. **API Gateway**: RESTful endpoints for initial data and fallback scenarios

## Components and Interfaces

### 1. Batch Data Fetcher Service

**Purpose**: Efficiently fetch multiple stock quotes from BSE API in batches

**Interface**:
```python
class BatchDataFetcher:
    def fetch_batch_quotes(self, symbols: List[str]) -> Dict[str, StockQuote]
    def schedule_periodic_updates(self, interval: int = 5)
    def add_symbol_to_watch(self, symbol: str)
    def remove_symbol_from_watch(self, symbol: str)
```

**Key Features**:
- Batches up to 20 symbols per BSE API call
- Implements exponential backoff for failed requests
- Prioritizes frequently requested symbols
- Maintains separate update frequencies for different symbol tiers

### 2. Redis Cache Manager

**Purpose**: Provide fast data access and real-time update distribution

**Interface**:
```python
class CacheManager:
    def set_stock_data(self, symbol: str, data: StockQuote, ttl: int = 300)
    def get_stock_data(self, symbol: str) -> Optional[StockQuote]
    def publish_update(self, symbol: str, data: StockQuote)
    def subscribe_to_updates(self, callback: Callable)
```

**Cache Strategy**:
- **L1 Cache**: In-memory Python dict for ultra-fast access (1-2 second TTL)
- **L2 Cache**: Redis with 5-minute TTL for persistence
- **Pub/Sub**: Redis channels for broadcasting updates to all connected clients

### 3. WebSocket Connection Manager

**Purpose**: Handle real-time bidirectional communication with clients

**Interface**:
```python
class WebSocketManager:
    def handle_client_connection(self, websocket, path)
    def broadcast_stock_update(self, symbol: str, data: StockQuote)
    def send_to_client(self, client_id: str, message: dict)
    def handle_client_subscription(self, client_id: str, symbols: List[str])
```

**Features**:
- Connection pooling and automatic reconnection
- Client-specific symbol subscriptions
- Message queuing for disconnected clients
- Heartbeat mechanism for connection health

### 4. Data Compression Service

**Purpose**: Minimize bandwidth usage for real-time updates

**Interface**:
```python
class CompressionService:
    def compress_stock_data(self, data: Dict) -> bytes
    def decompress_stock_data(self, compressed_data: bytes) -> Dict
    def create_delta_update(self, old_data: Dict, new_data: Dict) -> Dict
```

**Compression Strategies**:
- **Delta Updates**: Send only changed fields
- **Binary Encoding**: Use MessagePack for smaller payloads
- **Batch Compression**: Group multiple updates for better compression ratios

## Data Models

### StockQuote Model
```python
@dataclass
class StockQuote:
    symbol: str
    company_name: str
    current_price: float
    change: float
    percent_change: float
    volume: int
    timestamp: datetime
    bid_price: Optional[float] = None
    ask_price: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
```

### WebSocket Message Format
```json
{
    "type": "stock_update",
    "data": {
        "symbol": "500325",
        "price": 2501.50,
        "change": 1.50,
        "pChange": 0.06,
        "timestamp": "2024-01-15T10:30:00Z"
    },
    "compression": "delta"
}
```

### Cache Key Structure
```
stock:quote:{symbol}          # Individual stock data
stock:batch:{batch_id}        # Batch processing status
client:subscription:{client_id} # Client symbol subscriptions
metrics:performance:{date}    # Performance metrics
```

## Error Handling

### 1. BSE API Failures
- **Circuit Breaker Pattern**: Stop calling failing API after threshold
- **Fallback Strategy**: Serve cached data with staleness indicators
- **Retry Logic**: Exponential backoff with jitter
- **Health Checks**: Monitor API availability and response times

### 2. WebSocket Connection Issues
- **Automatic Reconnection**: Client-side reconnection with exponential backoff
- **Message Queuing**: Store updates for disconnected clients (up to 5 minutes)
- **Connection Pooling**: Reuse connections and handle connection limits
- **Graceful Degradation**: Fall back to HTTP polling if WebSocket fails

### 3. Cache Failures
- **Redis Failover**: Implement Redis Sentinel for high availability
- **Memory Fallback**: Use in-memory cache if Redis is unavailable
- **Data Validation**: Verify cache data integrity before serving
- **Cache Warming**: Pre-populate cache with essential stock data

### 4. Performance Monitoring
```python
class PerformanceMonitor:
    def track_api_response_time(self, endpoint: str, duration: float)
    def track_cache_hit_rate(self, cache_type: str, hit: bool)
    def track_websocket_connections(self, count: int)
    def alert_on_threshold_breach(self, metric: str, value: float)
```

## Testing Strategy

### 1. Unit Tests
- **Data Fetcher**: Mock BSE API responses and test batch processing
- **Cache Manager**: Test Redis operations and TTL behavior
- **WebSocket Manager**: Test connection handling and message broadcasting
- **Compression Service**: Verify compression/decompression accuracy

### 2. Integration Tests
- **End-to-End Data Flow**: Test complete pipeline from BSE API to frontend
- **WebSocket Communication**: Test real-time updates and reconnection
- **Cache Consistency**: Verify data consistency across cache layers
- **Error Scenarios**: Test system behavior under various failure conditions

### 3. Performance Tests
- **Load Testing**: Simulate 100+ concurrent WebSocket connections
- **Stress Testing**: Test system behavior under high API call volumes
- **Latency Testing**: Measure end-to-end update latency
- **Memory Testing**: Monitor memory usage under sustained load

### 4. Frontend Integration Tests
- **Real-time Updates**: Verify frontend receives and displays updates correctly
- **Reconnection Logic**: Test frontend behavior during connection drops
- **Data Synchronization**: Ensure frontend state matches backend data
- **User Experience**: Test responsiveness under various network conditions

## Performance Targets

- **Initial Load Time**: < 2 seconds for 20 stocks
- **Update Latency**: < 500ms from BSE data change to frontend display
- **Concurrent Users**: Support 100+ simultaneous WebSocket connections
- **API Efficiency**: Reduce BSE API calls by 80% through batching and caching
- **Memory Usage**: < 512MB for cache and connection management
- **CPU Usage**: < 50% under normal load conditions