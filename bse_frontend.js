// --- BSE Stock data ---
let bseStocks = {};
let markets = [];
let selected = null;
let chart = null;
let portfolio = {
    '500325': { quantity: 10, avgPrice: 2500 },
    '500570': { quantity: 50, avgPrice: 500 },
    '500209': { quantity: 100, avgPrice: 1500 }
};

function renderPortfolio() {
    const portfolioContainer = document.querySelector('#portfolio-list');
    portfolioContainer.innerHTML = '';
    let totalValue = 0;

    for (const symbol in portfolio) {
        const stock = markets.find(m => m.symbol === symbol);
        if (stock) {
            const holding = portfolio[symbol];
            const currentValue = stock.price * holding.quantity;
            totalValue += currentValue;

            const row = document.createElement('div');
            row.className = 'flex items-center justify-between';
            row.innerHTML = `
                <div>${stock.name}</div>
                <div>
                    <span class="font-medium">${holding.quantity}</span> 
                    <span class="text-slate-400">(~₹${fmt(currentValue)})</span>
                </div>
            `;
            portfolioContainer.appendChild(row);
        }
    }

    const totalValueEl = document.getElementById('portfolio-total-value');
    totalValueEl.textContent = `~₹${fmt(totalValue)}`;
}

// --- Performance Optimization State ---
class PerformanceOptimizer {
  constructor() {
    this.domUpdateQueue = new Map();
    this.animationFrameId = null;
    this.lastUpdateTime = 0;
    this.updateThrottle = 16; // ~60fps
    this.loadingStates = new Map();
    this.validationRules = new Map();
    this.errorStates = new Map();
  }

  // Batch DOM updates for better performance
  queueDOMUpdate(elementId, updateFn) {
    this.domUpdateQueue.set(elementId, updateFn);
    
    if (!this.animationFrameId) {
      this.animationFrameId = requestAnimationFrame(() => {
        this.flushDOMUpdates();
      });
    }
  }

  flushDOMUpdates() {
    const now = performance.now();
    
    // Throttle updates to maintain 60fps
    if (now - this.lastUpdateTime < this.updateThrottle) {
      this.animationFrameId = requestAnimationFrame(() => {
        this.flushDOMUpdates();
      });
      return;
    }

    // Apply all queued updates in a single frame
    this.domUpdateQueue.forEach((updateFn, elementId) => {
      try {
        updateFn();
      } catch (error) {
        console.error(`DOM update failed for ${elementId}:`, error);
      }
    });

    this.domUpdateQueue.clear();
    this.animationFrameId = null;
    this.lastUpdateTime = now;
  }

  // Loading state management
  setLoadingState(elementId, isLoading, message = 'Loading...') {
    this.loadingStates.set(elementId, { isLoading, message });
    this.updateLoadingUI(elementId, isLoading, message);
  }

  updateLoadingUI(elementId, isLoading, message) {
    const element = document.getElementById(elementId);
    if (!element) return;

    if (isLoading) {
      element.classList.add('loading');
      const loadingIndicator = element.querySelector('.loading-indicator') || this.createLoadingIndicator();
      loadingIndicator.textContent = message;
      if (!element.contains(loadingIndicator)) {
        element.appendChild(loadingIndicator);
      }
    } else {
      element.classList.remove('loading');
      const loadingIndicator = element.querySelector('.loading-indicator');
      if (loadingIndicator) {
        loadingIndicator.remove();
      }
    }
  }

  createLoadingIndicator() {
    const indicator = document.createElement('div');
    indicator.className = 'loading-indicator flex items-center gap-2 text-sm text-slate-400 p-2';
    indicator.innerHTML = `
      <div class="animate-spin w-4 h-4 border-2 border-slate-600 border-t-indigo-400 rounded-full"></div>
      <span>Loading...</span>
    `;
    return indicator;
  }

  // Client-side validation
  addValidationRule(fieldId, rule) {
    if (!this.validationRules.has(fieldId)) {
      this.validationRules.set(fieldId, []);
    }
    this.validationRules.get(fieldId).push(rule);
  }

  validateField(fieldId, value) {
    const rules = this.validationRules.get(fieldId) || [];
    const errors = [];

    for (const rule of rules) {
      const result = rule.validate(value);
      if (!result.valid) {
        errors.push(result.message);
      }
    }

    this.updateValidationUI(fieldId, errors);
    return errors.length === 0;
  }

  updateValidationUI(fieldId, errors) {
    const field = document.getElementById(fieldId);
    if (!field) return;

    // Remove existing error indicators
    const existingError = field.parentElement.querySelector('.validation-error');
    if (existingError) {
      existingError.remove();
    }

    field.classList.remove('border-red-500', 'border-green-500');

    if (errors.length > 0) {
      field.classList.add('border-red-500');
      const errorDiv = document.createElement('div');
      errorDiv.className = 'validation-error text-xs text-red-400 mt-1';
      errorDiv.textContent = errors[0]; // Show first error
      field.parentElement.appendChild(errorDiv);
      this.errorStates.set(fieldId, errors);
    } else {
      field.classList.add('border-green-500');
      this.errorStates.delete(fieldId);
    }
  }

  hasValidationErrors() {
    return this.errorStates.size > 0;
  }

  // Efficient price change animations
  animatePriceChange(elementId, newValue, oldValue) {
    const element = document.getElementById(elementId);
    if (!element) return;

    const isIncrease = newValue > oldValue;
    const changeClass = isIncrease ? 'price-increase' : 'price-decrease';
    
    element.classList.add(changeClass);
    
    // Remove animation class after animation completes
    setTimeout(() => {
      element.classList.remove(changeClass);
    }, 600);
  }
}

// Global performance optimizer instance
const perfOptimizer = new PerformanceOptimizer();

// Performance monitoring class
class PerformanceMonitor {
  constructor() {
    this.metrics = {
      latency: [],
      frameRate: [],
      memoryUsage: [],
      connectionQuality: 'unknown'
    };
    this.lastFrameTime = performance.now();
    this.frameCount = 0;
    this.isMonitoring = false;
  }

  startMonitoring() {
    this.isMonitoring = true;
    this.monitorFrameRate();
    this.monitorMemoryUsage();
    this.updatePerformanceDisplay();
  }

  stopMonitoring() {
    this.isMonitoring = false;
  }

  recordLatency(startTime) {
    const latency = performance.now() - startTime;
    this.metrics.latency.push(latency);
    
    // Keep only last 100 measurements
    if (this.metrics.latency.length > 100) {
      this.metrics.latency.shift();
    }
    
    return latency;
  }

  getAverageLatency() {
    if (this.metrics.latency.length === 0) return 0;
    return this.metrics.latency.reduce((a, b) => a + b, 0) / this.metrics.latency.length;
  }

  monitorFrameRate() {
    if (!this.isMonitoring) return;
    
    const now = performance.now();
    const delta = now - this.lastFrameTime;
    
    if (delta >= 1000) { // Calculate FPS every second
      const fps = Math.round((this.frameCount * 1000) / delta);
      this.metrics.frameRate.push(fps);
      
      // Keep only last 60 measurements (1 minute)
      if (this.metrics.frameRate.length > 60) {
        this.metrics.frameRate.shift();
      }
      
      this.frameCount = 0;
      this.lastFrameTime = now;
    }
    
    this.frameCount++;
    requestAnimationFrame(() => this.monitorFrameRate());
  }

  monitorMemoryUsage() {
    if (!this.isMonitoring) return;
    
    if (performance.memory) {
      const memInfo = {
        used: Math.round(performance.memory.usedJSHeapSize / 1048576), // MB
        total: Math.round(performance.memory.totalJSHeapSize / 1048576), // MB
        limit: Math.round(performance.memory.jsHeapSizeLimit / 1048576) // MB
      };
      
      this.metrics.memoryUsage.push(memInfo);
      
      // Keep only last 60 measurements
      if (this.metrics.memoryUsage.length > 60) {
        this.metrics.memoryUsage.shift();
      }
    }
    
    setTimeout(() => this.monitorMemoryUsage(), 5000); // Check every 5 seconds
  }

  updatePerformanceDisplay() {
    if (!this.isMonitoring) return;
    
    const perfDisplay = document.getElementById('perf-display') || this.createPerformanceDisplay();
    
    const avgLatency = this.getAverageLatency();
    const currentFPS = this.metrics.frameRate.length > 0 ? 
      this.metrics.frameRate[this.metrics.frameRate.length - 1] : 0;
    const currentMem = this.metrics.memoryUsage.length > 0 ? 
      this.metrics.memoryUsage[this.metrics.memoryUsage.length - 1] : null;
    
    perfDisplay.innerHTML = `
      <div class="flex items-center gap-4 text-xs">
        <div class="flex items-center gap-1">
          <span class="text-slate-400">Latency:</span>
          <span class="${avgLatency < 100 ? 'text-green-400' : avgLatency < 300 ? 'text-yellow-400' : 'text-red-400'}">
            ${avgLatency.toFixed(0)}ms
          </span>
        </div>
        <div class="flex items-center gap-1">
          <span class="text-slate-400">FPS:</span>
          <span class="${currentFPS >= 55 ? 'text-green-400' : currentFPS >= 30 ? 'text-yellow-400' : 'text-red-400'}">
            ${currentFPS}
          </span>
        </div>
        ${currentMem ? `
          <div class="flex items-center gap-1">
            <span class="text-slate-400">Mem:</span>
            <span class="${currentMem.used < 50 ? 'text-green-400' : currentMem.used < 100 ? 'text-yellow-400' : 'text-red-400'}">
              ${currentMem.used}MB
            </span>
          </div>
        ` : ''}
      </div>
    `;
    
    setTimeout(() => this.updatePerformanceDisplay(), 1000);
  }

  createPerformanceDisplay() {
    const display = document.createElement('div');
    display.id = 'perf-display';
    display.className = 'perf-metrics fixed bottom-4 right-4 z-50';
    document.body.appendChild(display);
    return display;
  }
}

// Global performance monitor instance
const perfMonitor = new PerformanceMonitor();

// --- WebSocket Connection Management ---
class WebSocketManager {
  constructor() {
    this.ws = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 10;
    this.reconnectDelay = 1000; // Start with 1 second
    this.maxReconnectDelay = 30000; // Max 30 seconds
    this.isConnected = false;
    this.subscriptions = new Set();
    this.messageQueue = [];
    this.heartbeatInterval = null;
    this.reconnectTimeout = null;
    
    // Client-side cache for stock data
    this.cache = new Map();
    this.cacheTimeout = 5000; // 5 seconds cache timeout
    
    // Connection status callbacks
    this.onConnected = null;
    this.onDisconnected = null;
    this.onStockUpdate = null;
    this.onOrderUpdate = null;
  }

  connect() {
    try {
      const wsUrl = `http://localhost:3002`;
      console.log('Connecting to WebSocket:', wsUrl);

      this.ws = io(wsUrl, {
        transports: ['websocket'],
        reconnectionAttempts: this.maxReconnectAttempts,
        timeout: 20000,
      });

      this.ws.on('connect', () => {
        console.log('WebSocket connected');
        this.isConnected = true;
        this.reconnectAttempts = 0;
        this.reconnectDelay = 1000;
        
        this.updateConnectionStatus(true);
        this.flushMessageQueue();
        this.resubscribe();
        this.startHeartbeat();
        
        if (this.onConnected) this.onConnected();
      });

      this.ws.on('stock_update', (data) => {
        this.handleMessage(data);
      });
      
      this.ws.on('message', (data) => {
        this.handleMessage(data);
      });

      this.ws.on('disconnect', () => {
        console.log('WebSocket disconnected');
        this.isConnected = false;
        this.updateConnectionStatus(false);
        this.stopHeartbeat();
        
        if (this.onDisconnected) this.onDisconnected();
        
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
          this.scheduleReconnect();
        }
      });

      this.ws.on('connect_error', (error) => {
        console.error('WebSocket connection error:', error);
        this.updateConnectionStatus(false);
        // Reconnect logic is handled by scheduleReconnect
      });

    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      this.scheduleReconnect();
    }
  }

  scheduleReconnect() {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
    }

    this.reconnectAttempts++;
    const delay = Math.min(
      this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1),
      this.maxReconnectDelay
    );

    console.log(`Scheduling reconnect attempt ${this.reconnectAttempts} in ${delay}ms`);
    
    this.reconnectTimeout = setTimeout(() => {
      this.connect();
    }, delay);
  }

  handleMessage(message) {
    switch (message.type) {
      case 'stock_update':
        this.handleStockUpdate(message.data);
        break;
      case 'order_update':
        this.handleOrderUpdate(message.data);
        break;
      case 'market_status':
        this.handleMarketStatus(message.data);
        break;
      case 'pong':
        // Heartbeat response
        break;
      default:
        console.log('Unknown message type:', message.type);
    }
  }

  handleStockUpdate(data) {
    // Update cache
    this.updateCache(data.symbol, data);
    
    // Update UI if this is the selected stock or in markets list
    if (selected && selected.symbol === data.symbol) {
      this.updateSelectedStock(data);
    }
    
    // Update market list
    this.updateMarketData(data);
    
    // Call callback if set
    if (this.onStockUpdate) {
      this.onStockUpdate(data);
    }
  }

  handleOrderUpdate(data) {
    // Update order status in UI
    this.updateOrderStatus(data);
    
    if (this.onOrderUpdate) {
      this.onOrderUpdate(data);
    }
  }

  handleMarketStatus(data) {
    // Update market status indicator
    this.updateMarketStatus(data);
  }

  updateCache(symbol, data) {
    this.cache.set(symbol, {
      data: data,
      timestamp: Date.now()
    });
  }

  getCachedData(symbol) {
    const cached = this.cache.get(symbol);
    if (cached && (Date.now() - cached.timestamp) < this.cacheTimeout) {
      return cached.data;
    }
    return null;
  }

  subscribe(symbol) {
    this.subscriptions.add(symbol);
    if (this.isConnected) {
      this.ws.emit('subscribe', { symbols: [symbol] });
    }
  }

  unsubscribe(symbol) {
    this.subscriptions.delete(symbol);
    if (this.isConnected) {
      this.ws.emit('unsubscribe', { symbols: [symbol] });
    }
  }

  resubscribe() {
    if (this.subscriptions.size > 0) {
        this.ws.emit('subscribe', { symbols: Array.from(this.subscriptions) });
    }
  }

  send(message) {
    if (this.isConnected && this.ws.connected) {
        this.ws.emit(message.type, message.data);
    } else {
      // Queue message for later
      this.messageQueue.push(message);
    }
  }

  flushMessageQueue() {
    while (this.messageQueue.length > 0) {
      const message = this.messageQueue.shift();
      this.send(message);
    }
  }

  startHeartbeat() {
    this.heartbeatInterval = setInterval(() => {
      if (this.isConnected) {
        this.ws.emit('ping');
      }
    }, 30000); // Send ping every 30 seconds
  }

  stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  updateConnectionStatus(connected) {
    // Update connection indicator in header with enhanced status
    const statusEl = document.querySelector('.connection-status') || this.createConnectionStatus();
    
    // Add connection quality indicator
    const quality = this.getConnectionQuality();
    const qualityColor = quality === 'excellent' ? 'bg-green-400' : 
                        quality === 'good' ? 'bg-yellow-400' : 
                        quality === 'poor' ? 'bg-orange-400' : 'bg-red-400';
    
    statusEl.className = `connection-status flex items-center gap-2 text-sm px-3 py-2 rounded-lg glass transition-all duration-300 ${
      connected ? 'text-green-300' : 'text-red-300'
    }`;
    
    statusEl.innerHTML = `
      <div class="relative">
        <div class="w-2 h-2 rounded-full ${connected ? qualityColor : 'bg-red-400'}"></div>
        ${connected ? '<div class="absolute inset-0 w-2 h-2 rounded-full animate-ping bg-green-400 opacity-75"></div>' : ''}
      </div>
      <span>${connected ? this.getConnectionStatusText(quality) : 'Disconnected'}</span>
      ${connected ? `<span class="text-xs text-slate-400">(${this.reconnectAttempts > 0 ? 'Reconnected' : 'Live'})</span>` : ''}
    `;
  }

  getConnectionQuality() {
    const avgLatency = perfMonitor.getAverageLatency();
    if (avgLatency < 100) return 'excellent';
    if (avgLatency < 300) return 'good';
    if (avgLatency < 1000) return 'poor';
    return 'bad';
  }

  getConnectionStatusText(quality) {
    switch (quality) {
      case 'excellent': return 'Connected';
      case 'good': return 'Connected';
      case 'poor': return 'Slow Connection';
      case 'bad': return 'Poor Connection';
      default: return 'Connected';
    }
  }

  createConnectionStatus() {
    const header = document.querySelector('header .flex.items-center.gap-3');
    const statusEl = document.createElement('div');
    header.insertBefore(statusEl, header.firstChild);
    return statusEl;
  }

  updateSelectedStock(data) {
    const oldPrice = selected.price;
    
    // Update selected stock data
    selected.price = parseFloat(data.price || data.current_price);
    selected.change = parseFloat(data.change);
    selected.pChange = parseFloat(data.percent_change || data.pChange);
    
    // Queue optimized DOM updates
    perfOptimizer.queueDOMUpdate('selected-price', () => {
      const priceEl = document.getElementById("selected-price");
      if (priceEl) {
        priceEl.innerText = "₹" + fmt(selected.price);
        // Animate price change if significant
        if (Math.abs(selected.price - oldPrice) > 0.01) {
          perfOptimizer.animatePriceChange('selected-price', selected.price, oldPrice);
        }
      }
    });

    perfOptimizer.queueDOMUpdate('selected-symbol', () => {
      const symbolEl = document.getElementById("selected-symbol");
      if (symbolEl) {
        symbolEl.innerText = data.company_name || data.company || selected.name;
      }
    });

    perfOptimizer.queueDOMUpdate('selected-change', () => {
      const changeEl = document.getElementById("selected-change");
      if (changeEl) {
        changeEl.innerText = (selected.pChange >= 0 ? '+' : '') + selected.pChange.toFixed(2) + "%";
        const up = selected.pChange >= 0;
        changeEl.className = `text-sm px-2 py-1 rounded-md transition-all duration-300 ${
          up ? 'bg-green-900/30 text-green-300' : 'bg-red-900/30 text-red-300'
        }`;
      }
    });
    
    // Update chart with new data point (throttled)
    this.updateChart(selected.price);
    
    // Update order book (throttled)
    perfOptimizer.queueDOMUpdate('order-book', () => {
      renderOrderBook();
    });
  }

  updateMarketData(data) {
    const marketIndex = markets.findIndex(m => m.symbol === data.symbol);
    if (marketIndex !== -1) {
      markets[marketIndex].price = parseFloat(data.price || data.current_price);
      markets[marketIndex].change = parseFloat(data.change);
      markets[marketIndex].pChange = parseFloat(data.percent_change || data.pChange);
      
      // Re-render markets list
      renderMarkets(markets);
    }
  }

  updateChart(newPrice) {
    if (!chart || !selected) return;
    
    // Enhanced throttling with adaptive update frequency
    const now = Date.now();
    const timeSinceLastUpdate = now - (this.lastChartUpdate || 0);
    const minUpdateInterval = this.getOptimalUpdateInterval();
    
    if (timeSinceLastUpdate < minUpdateInterval) {
      // Queue update for later if too frequent
      if (!this.pendingChartUpdate) {
        this.pendingChartUpdate = setTimeout(() => {
          this.pendingChartUpdate = null;
          this.updateChart(newPrice);
        }, minUpdateInterval - timeSinceLastUpdate);
      }
      return;
    }
    
    this.lastChartUpdate = now;
    
    const timeLabel = new Date().toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'});
    const priceValue = Number(newPrice.toFixed(2));
    
    // Batch chart updates for smooth animation with performance monitoring
    const updateStart = performance.now();
    
    requestAnimationFrame(() => {
      try {
        // Efficient data management
        const maxDataPoints = this.getOptimalDataPoints();
        
        chart.data.labels.push(timeLabel);
        chart.data.datasets[0].data.push(priceValue);
        
        // Dynamic data point management based on performance
        if (chart.data.labels.length > maxDataPoints) {
          const removeCount = Math.max(1, Math.floor(maxDataPoints * 0.1));
          chart.data.labels.splice(0, removeCount);
          chart.data.datasets[0].data.splice(0, removeCount);
        }
        
        // Adaptive update mode based on performance
        const updateMode = this.getOptimalUpdateMode();
        chart.update(updateMode);
        
        // Update chart styling with smooth transitions
        this.updateChartStyling();
        
        // Record performance metrics
        perfMonitor.recordLatency(updateStart);
        
      } catch (error) {
        console.error('Chart update failed:', error);
        // Fallback to basic update
        chart.update('none');
      }
    });
  }

  getOptimalUpdateInterval() {
    const avgFPS = perfMonitor.metrics.frameRate.length > 0 ? 
      perfMonitor.metrics.frameRate.reduce((a, b) => a + b, 0) / perfMonitor.metrics.frameRate.length : 60;
    
    // Adjust update frequency based on performance
    if (avgFPS >= 55) return 500;  // High performance: 2 updates/sec
    if (avgFPS >= 30) return 1000; // Medium performance: 1 update/sec
    return 2000; // Low performance: 0.5 updates/sec
  }

  getOptimalDataPoints() {
    const memUsage = perfMonitor.metrics.memoryUsage.length > 0 ? 
      perfMonitor.metrics.memoryUsage[perfMonitor.metrics.memoryUsage.length - 1] : null;
    
    if (!memUsage) return 120;
    
    // Adjust data points based on memory usage
    if (memUsage.used < 50) return 200;  // Low memory: more data points
    if (memUsage.used < 100) return 120; // Medium memory: standard
    return 60; // High memory: fewer data points
  }

  getOptimalUpdateMode() {
    const avgLatency = perfMonitor.getAverageLatency();
    
    // Choose update mode based on performance
    if (avgLatency < 50) return 'active';     // Smooth animations
    if (avgLatency < 150) return 'resize';    // Basic animations
    return 'none'; // No animations for better performance
  }

  updateChartStyling() {
    const dataLength = chart.data.datasets[0].data.length;
    if (dataLength >= 2) {
      const currentPrice = chart.data.datasets[0].data[dataLength - 1];
      const previousPrice = chart.data.datasets[0].data[dataLength - 2];
      const isIncreasing = currentPrice > previousPrice;
      
      // Smooth color transitions
      const targetBorderColor = isIncreasing ? '#22c55e' : '#ef4444';
      const targetBgColor = isIncreasing ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)';
      
      // Apply colors with transition effect
      chart.data.datasets[0].borderColor = targetBorderColor;
      chart.data.datasets[0].backgroundColor = targetBgColor;
      
      // Add gradient effect for better visual appeal
      const ctx = chart.ctx;
      const gradient = ctx.createLinearGradient(0, 0, 0, chart.height);
      gradient.addColorStop(0, targetBgColor);
      gradient.addColorStop(1, 'rgba(0, 0, 0, 0)');
      chart.data.datasets[0].backgroundColor = gradient;
    }
  }

  updateOrderStatus(orderData) {
    // Find and update order in open orders list
    const ordersContainer = document.getElementById('openOrders');
    const orderElements = ordersContainer.querySelectorAll('[data-order-id]');
    
    orderElements.forEach(el => {
      if (el.dataset.orderId === orderData.id) {
        // Update order status
        const statusEl = el.querySelector('.order-status');
        if (statusEl) {
          statusEl.textContent = orderData.status;
          statusEl.className = `order-status text-xs ${
            orderData.status === 'filled' ? 'text-green-300' :
            orderData.status === 'cancelled' ? 'text-red-300' :
            'text-yellow-300'
          }`;
        }
      }
    });
  }

  updateMarketStatus(statusData) {
    // Update market status indicator
    const marketStatusEl = document.querySelector('.market-status') || this.createMarketStatus();
    marketStatusEl.textContent = statusData.status;
    marketStatusEl.className = `market-status text-sm px-2 py-1 rounded-md ${
      statusData.status === 'open' ? 'bg-green-900/30 text-green-300' :
      statusData.status === 'closed' ? 'bg-red-900/30 text-red-300' :
      'bg-yellow-900/30 text-yellow-300'
    }`;
  }

  createMarketStatus() {
    const header = document.querySelector('header h1').parentElement;
    const statusEl = document.createElement('div');
    statusEl.className = 'market-status text-sm px-2 py-1 rounded-md bg-slate-800/40 text-slate-300';
    statusEl.textContent = 'Market Status';
    header.appendChild(statusEl);
    return statusEl;
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
    }
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
    }
    this.stopHeartbeat();
  }
}

// Global WebSocket manager instance
const wsManager = new WebSocketManager();

// Enhanced data validation utilities
class DataValidator {
  static validateStockData(data) {
    const errors = [];
    
    if (!data || typeof data !== 'object') {
      errors.push('Invalid data format');
      return { valid: false, errors };
    }
    
    // Required fields validation
    const requiredFields = ['symbol', 'price'];
    requiredFields.forEach(field => {
      if (!(field in data)) {
        errors.push(`Missing required field: ${field}`);
      }
    });
    
    // Data type validation
    if (data.price !== undefined && (isNaN(data.price) || data.price < 0)) {
      errors.push('Invalid price value');
    }
    
    if (data.change !== undefined && isNaN(data.change)) {
      errors.push('Invalid change value');
    }
    
    if (data.pChange !== undefined && isNaN(data.pChange)) {
      errors.push('Invalid percentage change value');
    }
    
    // Range validation
    if (data.price > 1000000) {
      errors.push('Price value seems unrealistic');
    }
    
    if (Math.abs(data.pChange) > 50) {
      errors.push('Percentage change seems unrealistic');
    }
    
    return { valid: errors.length === 0, errors };
  }
  
  static validateOrderData(orderData) {
    const errors = [];
    
    if (!orderData || typeof orderData !== 'object') {
      errors.push('Invalid order data format');
      return { valid: false, errors };
    }
    
    // Required fields
    const requiredFields = ['symbol', 'side', 'price', 'amount'];
    requiredFields.forEach(field => {
      if (!(field in orderData)) {
        errors.push(`Missing required field: ${field}`);
      }
    });
    
    // Side validation
    if (orderData.side && !['buy', 'sell'].includes(orderData.side.toLowerCase())) {
      errors.push('Invalid order side (must be buy or sell)');
    }
    
    // Price validation
    if (orderData.price !== undefined) {
      const price = parseFloat(orderData.price);
      if (isNaN(price) || price <= 0) {
        errors.push('Price must be a positive number');
      }
      if (price > 1000000) {
        errors.push('Price value is too high');
      }
    }
    
    // Amount validation
    if (orderData.amount !== undefined) {
      const amount = parseFloat(orderData.amount);
      if (isNaN(amount) || amount <= 0) {
        errors.push('Amount must be a positive number');
      }
      if (amount > 1000000) {
        errors.push('Amount value is too high');
      }
    }
    
    return { valid: errors.length === 0, errors };
  }
  
  static sanitizeInput(input) {
    if (typeof input === 'string') {
      return input.trim().replace(/[<>]/g, '');
    }
    return input;
  }
}

// Load BSE stocks from backend with enhanced loading states and validation
async function loadBSEStocks() {
  console.log('📡 Loading BSE stocks from backend...');
  
  // Show loading state with progress indicator
  perfOptimizer.setLoadingState('market-list', true, 'Loading market data...');
  
  const loadStart = performance.now();
  
  try {
    // Add timeout for better error handling
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout
    
    const response = await fetch('http://localhost:3002/api/stocks', {
      signal: controller.signal,
      headers: {
        'Accept': 'application/json',
        'Cache-Control': 'no-cache'
      }
    });
    
    clearTimeout(timeoutId);
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const responseData = await response.json();
    
    // Enhanced data validation
    if (!responseData || typeof responseData !== 'object') {
      throw new Error('Invalid response format received');
    }
    
    // Extract the actual stock data from the response
    const rawData = responseData.data || responseData;
    
    if (!rawData || typeof rawData !== 'object') {
      throw new Error('Invalid stock data format received');
    }
    
    // Validate each stock entry
    const validatedStocks = {};
    let invalidCount = 0;
    
    Object.entries(rawData).forEach(([symbol, name]) => {
      if (typeof symbol === 'string' && typeof name === 'string' && symbol.length > 0) {
        validatedStocks[DataValidator.sanitizeInput(symbol)] = DataValidator.sanitizeInput(name);
      } else {
        invalidCount++;
      }
    });
    
    if (invalidCount > 0) {
      console.warn(`Filtered out ${invalidCount} invalid stock entries`);
    }
    
    bseStocks = validatedStocks;
    
    // Record performance metrics
    const loadTime = perfMonitor.recordLatency(loadStart);
    console.log(`✅ Loaded ${Object.keys(bseStocks).length} stocks in ${loadTime.toFixed(2)}ms`);
    console.log('📋 First 5 stocks:', Object.entries(bseStocks).slice(0, 5));
    
    // Clear loading state
    perfOptimizer.setLoadingState('market-list', false);
    
    // Initialize markets with performance optimization
    await initializeMarkets();
    
    // Start performance monitoring
    perfMonitor.startMonitoring();
    
    return true;
    
  } catch (error) {
    console.error('Failed to load BSE stocks:', error);
    
    // Clear loading state and show error
    perfOptimizer.setLoadingState('market-list', false);
    showErrorMessage('Failed to load market data. Please check your connection and try again.');
    
    // Attempt to use cached data if available
    const cachedStocks = localStorage.getItem('bse_stocks_cache');
    if (cachedStocks) {
      try {
        bseStocks = JSON.parse(cachedStocks);
        showWarningMessage('Using cached market data. Some information may be outdated.');
        await initializeMarkets();
        return true;
      } catch (cacheError) {
        console.error('Failed to parse cached data:', cacheError);
      }
    }
    
    return false;
  }
}


// Utilities
const fmt = (n) => typeof n === 'number' ? n.toLocaleString(undefined, {minimumFractionDigits: n < 1 ? 6 : 2, maximumFractionDigits: 6}) : n;

// Fetch real BSE data (fallback when WebSocket is not available)
async function fetchBSE(symbol) {
  try {
    // Check cache first
    const cachedData = wsManager.getCachedData(symbol);
    if (cachedData) {
      wsManager.updateSelectedStock(cachedData);
      return;
    }
    
    const res = await fetch(`http://localhost:3002/api/quote/${symbol}`);
    const data = await res.json();
    if(data.price){
      // Update cache
      wsManager.updateCache(symbol, data);
      
      // Update selected stock
      selected.price = parseFloat(data.price);
      selected.change = parseFloat(data.change);
      selected.pChange = parseFloat(data.pChange);
      
      // Update market data
      const marketIndex = markets.findIndex(m => m.symbol === symbol);
      if(marketIndex !== -1) {
        markets[marketIndex] = {...selected};
      }
      
      // Update UI
      document.getElementById("selected-price").innerText = "₹" + fmt(data.price);
      document.getElementById("selected-symbol").innerText = data.company;
      document.getElementById("selected-change").innerText = data.pChange + "%";
      
      // Update change color
      const changeEl = document.getElementById("selected-change");
      const up = data.pChange >= 0;
      changeEl.className = 'text-sm px-2 py-1 rounded-md ' + (up? 'bg-green-900/30 text-green-300':'bg-red-900/30 text-red-300');
      
      renderMarkets(markets);
    }
  } catch (err) {
    console.error("Error fetching BSE:", err);
    // Show error state in UI
    showConnectionError("Failed to fetch stock data");
  }
}

// Enhanced notification system
class NotificationManager {
  constructor() {
    this.notifications = new Map();
    this.container = this.createContainer();
  }

  createContainer() {
    const container = document.createElement('div');
    container.id = 'notification-container';
    container.className = 'fixed top-4 right-4 z-50 space-y-2 max-w-sm';
    document.body.appendChild(container);
    return container;
  }

  show(message, type = 'info', duration = 5000, actions = []) {
    const id = Date.now().toString();
    const notification = this.createNotification(id, message, type, actions);
    
    this.container.appendChild(notification);
    this.notifications.set(id, notification);
    
    // Animate in
    requestAnimationFrame(() => {
      notification.style.transform = 'translateX(0)';
      notification.style.opacity = '1';
    });
    
    // Auto-hide after duration
    if (duration > 0) {
      setTimeout(() => this.hide(id), duration);
    }
    
    return id;
  }

  createNotification(id, message, type, actions) {
    const notification = document.createElement('div');
    notification.className = `notification transform translate-x-full opacity-0 transition-all duration-300 ease-out p-4 rounded-lg shadow-lg backdrop-blur-sm ${this.getTypeClasses(type)}`;
    notification.style.transform = 'translateX(100%)';
    notification.style.opacity = '0';
    
    const icon = this.getTypeIcon(type);
    
    notification.innerHTML = `
      <div class="flex items-start gap-3">
        <div class="flex-shrink-0 mt-0.5">
          ${icon}
        </div>
        <div class="flex-1 min-w-0">
          <div class="text-sm font-medium">${message}</div>
          ${actions.length > 0 ? `
            <div class="mt-2 flex gap-2">
              ${actions.map(action => `
                <button class="text-xs px-2 py-1 rounded bg-white/10 hover:bg-white/20 transition-colors" 
                        onclick="${action.handler}">
                  ${action.label}
                </button>
              `).join('')}
            </div>
          ` : ''}
        </div>
        <button class="flex-shrink-0 text-white/60 hover:text-white/80 transition-colors" 
                onclick="notificationManager.hide('${id}')">
          <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"></path>
          </svg>
        </button>
      </div>
    `;
    
    return notification;
  }

  getTypeClasses(type) {
    switch (type) {
      case 'success':
        return 'bg-green-900/80 text-green-100 border border-green-700/50';
      case 'error':
        return 'bg-red-900/80 text-red-100 border border-red-700/50';
      case 'warning':
        return 'bg-yellow-900/80 text-yellow-100 border border-yellow-700/50';
      case 'info':
      default:
        return 'bg-blue-900/80 text-blue-100 border border-blue-700/50';
    }
  }

  getTypeIcon(type) {
    switch (type) {
      case 'success':
        return `<svg class="w-5 h-5 text-green-400" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path>
        </svg>`;
      case 'error':
        return `<svg class="w-5 h-5 text-red-400" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"></path>
        </svg>`;
      case 'warning':
        return `<svg class="w-5 h-5 text-yellow-400" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"></path>
        </svg>`;
      case 'info':
      default:
        return `<svg class="w-5 h-5 text-blue-400" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"></path>
        </svg>`;
    }
  }

  hide(id) {
    const notification = this.notifications.get(id);
    if (notification) {
      notification.style.transform = 'translateX(100%)';
      notification.style.opacity = '0';
      
      setTimeout(() => {
        if (notification.parentNode) {
          notification.parentNode.removeChild(notification);
        }
        this.notifications.delete(id);
      }, 300);
    }
  }

  clear() {
    this.notifications.forEach((notification, id) => {
      this.hide(id);
    });
  }
}

// Global notification manager
const notificationManager = new NotificationManager();

// Show connection error in UI
function showConnectionError(message) {
  notificationManager.show(message, 'error', 8000, [
    {
      label: 'Retry',
      handler: 'loadBSEStocks()'
    }
  ]);
}

// Show connection success
function showConnectionSuccess(message) {
  notificationManager.show(message, 'success', 3000);
}

// Show connection warning
function showConnectionWarning(message) {
  notificationManager.show(message, 'warning', 5000);
}

// Render market list with optimized updates and visual indicators
function renderMarkets(marketsToRender){
  const el = document.getElementById('market-list');
  
  // Use document fragment for efficient DOM manipulation
  const fragment = document.createDocumentFragment();
  
  marketsToRender.forEach((m, idx) => {
    const up = m.pChange >= 0;
    const isSelected = selected && selected.symbol === m.symbol;
    const isStale = m.isStale || (m.lastUpdate && Date.now() - m.lastUpdate > 30000);
    
    const row = document.createElement('div');
    row.className = `market-row flex items-center justify-between p-2 rounded-lg hover:bg-slate-800/30 transition-all duration-200 cursor-pointer ${
      isSelected ? 'bg-slate-800/50 ring-1 ring-indigo-500/30' : ''
    } ${isStale ? 'opacity-60' : ''}`;
    row.dataset.marketIndex = markets.findIndex(market => market.symbol === m.symbol);
    
    row.innerHTML = `
      <div class="flex items-center gap-2">
        <div class="flex flex-col">
          <div class="flex items-center gap-2">
            <div class="font-medium">${m.symbol}</div>
            ${isStale ? '<div class="w-1 h-1 bg-yellow-400 rounded-full" title="Stale data"></div>' : ''}
          </div>
          <div class="text-xs text-slate-400 truncate max-w-[120px]">${m.name}</div>
        </div>
      </div>
      <div class="text-right">
        <div class="text-sm font-medium">₹${fmt(m.price)}</div>
        <div class="text-xs flex items-center gap-1 ${up ? 'ticker-up' : 'ticker-down'}">
          <span class="inline-block w-0 h-0 border-l-[3px] border-r-[3px] border-transparent ${
            up ? 'border-b-[4px] border-b-green-400' : 'border-t-[4px] border-t-red-400'
          }"></span>
          ${up ? '+' : ''}${m.pChange.toFixed(2)}%
        </div>
      </div>
    `;
    
    fragment.appendChild(row);
  });
  
  // Replace content efficiently
  el.innerHTML = '';
  el.appendChild(fragment);
}

// Order book mock
function renderOrderBook(){
  const asks = document.getElementById('asks');
  const bids = document.getElementById('bids');
  asks.innerHTML = '';
  bids.innerHTML = '';
  for(let i=0;i<8;i++){
    const aPrice = (selected.price * (1 + 0.002*i)).toFixed(2);
    const bPrice = (selected.price * (1 - 0.002*i)).toFixed(2);
    const aRow = document.createElement('div');
    aRow.className = 'flex justify-between text-xs text-slate-300';
    aRow.innerHTML = `<div>${aPrice}</div><div>${(Math.random()*3).toFixed(3)}</div>`;
    asks.appendChild(aRow);
    const bRow = document.createElement('div');
    bRow.className = 'flex justify-between text-xs text-slate-300';
    bRow.innerHTML = `<div class="text-green-300">${bPrice}</div><div>${(Math.random()*3).toFixed(3)}</div>`;
    bids.appendChild(bRow);
  }
}

async function fetchHistoricalData(symbol, timeframe) {
    try {
        const response = await fetch(`/api/historical-data/${symbol}/${timeframe}`);
        const data = await response.json();
        rebuildChart(data);
    } catch (error) {
        console.error('Failed to fetch historical data:', error);
    }
}

// Market selection
function selectMarket(idx){
  // Unsubscribe from previous selection if different
  if (selected && selected.symbol !== markets[idx].symbol) {
    // Keep subscription active for market list updates
  }
  
  selected = markets[idx];
  document.getElementById('selected-symbol').innerText = selected.name;
  
  // Subscribe to new selection for real-time updates
  wsManager.subscribe(selected.symbol);
  
  // Check cache first, then fetch if needed
  const cachedData = wsManager.getCachedData(selected.symbol);
  if (cachedData) {
    wsManager.updateSelectedStock(cachedData);
  } else {
    fetchBSE(selected.symbol);
  }
  
  renderOrderBook();
  const timeframe = document.getElementById('timeframe').value;
  fetchHistoricalData(selected.symbol, timeframe);
}

// Price box updater
function updateSelectedPrice(){
  const el = document.getElementById('selected-price');
  const changeEl = document.getElementById('selected-change');
  el.innerText = '₹' + fmt(selected.price);
  const up = selected.pChange >= 0;
  changeEl.innerText = (up?'+':'') + selected.pChange + '%';
  changeEl.className = 'text-sm px-2 py-1 rounded-md ' + (up? 'bg-green-900/30 text-green-300':'bg-red-900/30 text-red-300');
}

// Chart
function rebuildChart(historicalData){
  const ctx = document.getElementById('mainChart');
  if(chart){ chart.destroy(); }
  
  const labels = historicalData.map(d => d.time);
  const data = historicalData.map(d => d.price);

  chart = new Chart(ctx, {
    type: 'line',
    data: { labels, datasets: [{ label: selected.symbol, data, tension:0.25, borderWidth:2, pointRadius:0 }] },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { display: true, grid: { display: false }, ticks: { maxRotation:0 } },
        y: { display: true, grid: { color: 'rgba(255,255,255,0.03)' }, ticks: { callback: (v)=> '₹' + v } }
      }
    }
  });
}

// Enhanced form validation and handling
function setupFormValidation() {
  const priceInput = document.getElementById('price');
  const amountInput = document.getElementById('amount');
  const tradeForm = document.getElementById('tradeForm');
  
  // Add validation rules
  perfOptimizer.addValidationRule('price', {
    validate: (value) => {
      const price = parseFloat(value);
      if (isNaN(price) || price <= 0) {
        return { valid: false, message: 'Price must be a positive number' };
      }
      if (price > 1000000) {
        return { valid: false, message: 'Price is too high' };
      }
      if (selected && Math.abs(price - selected.price) / selected.price > 0.2) {
        return { valid: false, message: 'Price differs significantly from market price' };
      }
      return { valid: true };
    }
  });
  
  perfOptimizer.addValidationRule('amount', {
    validate: (value) => {
      const amount = parseFloat(value);
      if (isNaN(amount) || amount <= 0) {
        return { valid: false, message: 'Amount must be a positive number' };
      }
      if (amount > 1000000) {
        return { valid: false, message: 'Amount is too high' };
      }
      return { valid: true };
    }
  });
  
  // Real-time validation
  priceInput.addEventListener('input', (e) => {
    const value = DataValidator.sanitizeInput(e.target.value);
    perfOptimizer.validateField('price', value);
    updateEstimatedValue();
  });
  
  amountInput.addEventListener('input', (e) => {
    const value = DataValidator.sanitizeInput(e.target.value);
    perfOptimizer.validateField('amount', value);
    updateEstimatedValue();
  });
  
  // Form submission with validation
  const buyButton = document.getElementById('submitBuy');
  const sellButton = document.getElementById('submitSell');
  
  buyButton.addEventListener('click', (e) => {
    e.preventDefault();
    handleOrderSubmission('buy');
  });
  
  sellButton.addEventListener('click', (e) => {
    e.preventDefault();
    handleOrderSubmission('sell');
  });
}

function updateEstimatedValue() {
  const price = parseFloat(document.getElementById('price').value) || 0;
  const amount = parseFloat(document.getElementById('amount').value) || 0;
  const estValue = price * amount;
  
  const estValueEl = document.getElementById('estValue');
  estValueEl.textContent = '₹' + fmt(estValue);
  
  // Add visual feedback for large orders
  if (estValue > 100000) {
    estValueEl.className = 'text-yellow-400 font-semibold';
  } else {
    estValueEl.className = '';
  }
}

async function handleOrderSubmission(side) {
  const priceInput = document.getElementById('price');
  const amountInput = document.getElementById('amount');
  const submitButton = document.getElementById(side === 'buy' ? 'submitBuy' : 'submitSell');
  
  // Validate all fields
  const priceValid = perfOptimizer.validateField('price', priceInput.value);
  const amountValid = perfOptimizer.validateField('amount', amountInput.value);
  
  if (!priceValid || !amountValid) {
    notificationManager.show('Please fix validation errors before submitting', 'error');
    return;
  }
  
  if (perfOptimizer.hasValidationErrors()) {
    notificationManager.show('Please resolve all validation errors', 'error');
    return;
  }
  
  const orderData = {
    symbol: selected.symbol,
    side: side,
    price: parseFloat(priceInput.value),
    amount: parseFloat(amountInput.value),
    timestamp: new Date().toISOString()
  };
  
  // Additional validation
  const validation = DataValidator.validateOrderData(orderData);
  if (!validation.valid) {
    notificationManager.show(`Order validation failed: ${validation.errors[0]}`, 'error');
    return;
  }
  
  // Show loading state
  submitButton.disabled = true;
  submitButton.textContent = 'Placing Order...';
  
  try {
    // Simulate order placement (replace with actual API call)
    const response = await fetch('http://localhost:3002/api/orders', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(orderData)
    });
    
    if (!response.ok) {
      throw new Error(`Order failed: ${response.statusText}`);
    }
    
    const result = await response.json();
    
    // Show success notification
    notificationManager.show(
      `${side.toUpperCase()} order placed successfully for ${orderData.amount} shares at ₹${orderData.price}`,
      'success'
    );
    
    // Clear form
    priceInput.value = '';
    amountInput.value = '';
    updateEstimatedValue();
    
    // Add to order history
    addToOrderHistory(orderData, result);
    
  } catch (error) {
    console.error('Order submission failed:', error);
    notificationManager.show(`Failed to place order: ${error.message}`, 'error');
  } finally {
    // Reset button state
    submitButton.disabled = false;
    submitButton.textContent = side === 'buy' ? 'Place Buy' : 'Place Sell';
  }
}

function addToOrderHistory(orderData, result) {
  const historyContainer = document.getElementById('history');
  const orderElement = document.createElement('div');
  orderElement.className = 'flex justify-between text-xs p-2 rounded bg-slate-800/30';
  orderElement.innerHTML = `
    <div>
      <div class="font-medium">${orderData.symbol}</div>
      <div class="text-slate-400">${orderData.side.toUpperCase()} ${orderData.amount}</div>
    </div>
    <div class="text-right">
      <div>₹${fmt(orderData.price)}</div>
      <div class="text-slate-400">${new Date().toLocaleTimeString()}</div>
    </div>
  `;
  
  historyContainer.insertBefore(orderElement, historyContainer.firstChild);
  
  // Keep only last 10 orders
  while (historyContainer.children.length > 10) {
    historyContainer.removeChild(historyContainer.lastChild);
  }
}

// Initialize WebSocket connection and real-time updates
function startLive(){
  // Set up WebSocket callbacks
  wsManager.onConnected = () => {
    console.log('WebSocket connected - real-time updates active');
    showConnectionSuccess('Real-time updates connected');
  };
  
  wsManager.onDisconnected = () => {
    console.log('WebSocket disconnected - falling back to polling');
    showConnectionWarning('Real-time connection lost, using fallback mode');
    startPollingFallback();
  };
  
  wsManager.onStockUpdate = (data) => {
    console.log('Received stock update:', data);
    // Update is handled by wsManager.handleStockUpdate
  };
  
  wsManager.onOrderUpdate = (data) => {
    console.log('Received order update:', data);
    // Update is handled by wsManager.handleOrderUpdate
  };
  
  // Connect to WebSocket
  wsManager.connect();
  
  // Fallback polling for when WebSocket is not available
  startPollingFallback();
}

// Fallback polling mechanism
function startPollingFallback() {
  // Only poll if WebSocket is not connected
  const pollInterval = setInterval(() => {
    if (!wsManager.isConnected && selected) {
      // Check if we have recent cached data
      const cachedData = wsManager.getCachedData(selected.symbol);
      if (!cachedData) {
        fetchBSE(selected.symbol);
      }
    }
  }, 10000); // Poll every 10 seconds as fallback
  
  // Store interval ID for cleanup
  window.fallbackPollInterval = pollInterval;
}

// Show connection success message


// Enhanced trade form handling with validation and loading states
function setupTradeForm(){
  const priceInput = document.getElementById('price');
  const amountInput = document.getElementById('amount');
  const est = document.getElementById('estValue');
  
  // Add validation rules
  perfOptimizer.addValidationRule('price', {
    validate: (value) => {
      const num = parseFloat(value);
      if (isNaN(num) || num <= 0) {
        return { valid: false, message: 'Price must be a positive number' };
      }
      if (selected && Math.abs(num - selected.price) / selected.price > 0.1) {
        return { valid: false, message: 'Price differs significantly from market price' };
      }
      return { valid: true };
    }
  });
  
  perfOptimizer.addValidationRule('amount', {
    validate: (value) => {
      const num = parseFloat(value);
      if (isNaN(num) || num <= 0) {
        return { valid: false, message: 'Amount must be a positive number' };
      }
      if (num < 0.0001) {
        return { valid: false, message: 'Minimum amount is 0.0001' };
      }
      return { valid: true };
    }
  });
  
  // Debounced estimate update function
  let updateTimeout;
  function updateEst(){
    clearTimeout(updateTimeout);
    updateTimeout = setTimeout(() => {
      const p = Number(priceInput.value || selected?.price || 0);
      const a = Number(amountInput.value || 0);
      const total = p * a;
      
      perfOptimizer.queueDOMUpdate('estValue', () => {
        est.innerText = '₹' + fmt(total || 0);
        
        // Add visual feedback for large orders
        if (total > 100000) {
          est.classList.add('text-yellow-300');
          est.title = 'Large order value';
        } else {
          est.classList.remove('text-yellow-300');
          est.title = '';
        }
      });
    }, 150);
  }
  
  // Real-time validation and estimate updates
  priceInput.addEventListener('input', (e) => {
    perfOptimizer.validateField('price', e.target.value);
    updateEst();
  });
  
  amountInput.addEventListener('input', (e) => {
    perfOptimizer.validateField('amount', e.target.value);
    updateEst();
  });
  
  // Enhanced form submission with loading states
  document.getElementById('submitBuy').addEventListener('click', async (e) => {
    e.preventDefault();
    
    // Validate all fields
    const priceValid = perfOptimizer.validateField('price', priceInput.value);
    const amountValid = perfOptimizer.validateField('amount', amountInput.value);
    
    if (!priceValid || !amountValid) {
      showValidationError('Please fix the errors before submitting');
      return;
    }
    
    // Show loading state
    const button = e.target;
    const originalText = button.textContent;
    button.disabled = true;
    button.innerHTML = `
      <div class="flex items-center gap-2">
        <div class="animate-spin w-4 h-4 border-2 border-black border-t-transparent rounded-full"></div>
        Placing Order...
      </div>
    `;
    
    try {
      await placeOrder('buy', Number(priceInput.value || selected.price), Number(amountInput.value || 0));
    } finally {
      // Restore button state
      button.disabled = false;
      button.textContent = originalText;
    }
  });
  
  document.getElementById('submitSell').addEventListener('click', async (e) => {
    e.preventDefault();
    
    // Validate all fields
    const priceValid = perfOptimizer.validateField('price', priceInput.value);
    const amountValid = perfOptimizer.validateField('amount', amountInput.value);
    
    if (!priceValid || !amountValid) {
      showValidationError('Please fix the errors before submitting');
      return;
    }
    
    // Show loading state
    const button = e.target;
    const originalText = button.textContent;
    button.disabled = true;
    button.innerHTML = `
      <div class="flex items-center gap-2">
        <div class="animate-spin w-4 h-4 border-2 border-black border-t-transparent rounded-full"></div>
        Placing Order...
      </div>
    `;
    
    try {
      await placeOrder('sell', Number(priceInput.value || selected.price), Number(amountInput.value || 0));
    } finally {
      // Restore button state
      button.disabled = false;
      button.textContent = originalText;
    }
  });
}

function showValidationError(message) {
  const errorEl = document.getElementById('validation-error') || createValidationErrorElement();
  errorEl.textContent = message;
  errorEl.style.display = 'block';
  
  setTimeout(() => {
    errorEl.style.display = 'none';
  }, 5000);
}

function createValidationErrorElement() {
  const errorEl = document.createElement('div');
  errorEl.id = 'validation-error';
  errorEl.className = 'fixed top-4 left-1/2 transform -translate-x-1/2 bg-red-900/80 text-red-200 px-4 py-2 rounded-lg shadow-lg z-50';
  errorEl.style.display = 'none';
  document.body.appendChild(errorEl);
  return errorEl;
}

async function placeOrder(side, price, amount){
  if(!amount || amount<=0) return alert('Enter amount');
  
  const orderId = 'ORD-' + Math.random().toString(36).slice(2,9).toUpperCase();
  const orderData = {
    id: orderId,
    symbol: selected.symbol,
    side: side,
    price: price,
    amount: amount,
    timestamp: new Date().toISOString()
  };
  
  try {
    // Send order via WebSocket if connected
    if (wsManager.isConnected) {
      wsManager.send({
        type: 'place_order',
        data: orderData
      });
    } else {
      // Fallback to HTTP API
      const response = await fetch('http://localhost:3002/api/orders', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(orderData)
      });
      
      if (!response.ok) {
        throw new Error('Failed to place order');
      }
    }
    
    // Add order to UI immediately (optimistic update)
    addOrderToUI(orderData, 'pending');
    
    // Add to history
    addToHistory(side, amount, selected.symbol);

    // Update portfolio
    if (side === 'buy') {
        if (portfolio[selected.symbol]) {
            const holding = portfolio[selected.symbol];
            const newQuantity = holding.quantity + amount;
            const newAvgPrice = ((holding.avgPrice * holding.quantity) + (price * amount)) / newQuantity;
            holding.quantity = newQuantity;
            holding.avgPrice = newAvgPrice;
        } else {
            portfolio[selected.symbol] = { quantity: amount, avgPrice: price };
        }
    } else { // sell
        if (portfolio[selected.symbol]) {
            const holding = portfolio[selected.symbol];
            holding.quantity -= amount;
            if (holding.quantity <= 0) {
                delete portfolio[selected.symbol];
            }
        }
    }
    renderPortfolio();
    
    // Clear form
    document.getElementById('price').value = '';
    document.getElementById('amount').value = '';
    document.getElementById('estValue').innerText = '₹0.00';
    
  } catch (error) {
    console.error('Error placing order:', error);
    showConnectionError('Failed to place order: ' + error.message);
  }
}

function addOrderToUI(orderData, status = 'pending') {
  const el = document.getElementById('openOrders');
  const row = document.createElement('div');
  row.className = 'flex items-center justify-between text-sm bg-slate-900/20 p-2 rounded-md';
  row.setAttribute('data-order-id', orderData.id);
  
  const statusColor = status === 'filled' ? 'text-green-300' : 
                     status === 'cancelled' ? 'text-red-300' : 
                     'text-yellow-300';
  
  row.innerHTML = `
    <div>
      ${orderData.id} 
      <div class="text-xs text-slate-400">${orderData.side.toUpperCase()}</div>
      <div class="order-status text-xs ${statusColor}">${status}</div>
    </div>
    <div class="text-right">
      <div>${orderData.amount} @ ₹${fmt(orderData.price)}</div>
      <div class="text-xs text-slate-400">${new Date(orderData.timestamp).toLocaleTimeString()}</div>
    </div>
  `;
  el.prepend(row);
}

function addToHistory(side, amount, symbol) {
  const hist = document.getElementById('history');
  const hrow = document.createElement('div');
  hrow.className = 'flex items-center justify-between text-sm';
  hrow.innerHTML = `
    <div class="text-xs text-slate-400">${new Date().toLocaleTimeString()}</div>
    <div>${side==='buy'?'+':'-'}${fmt(amount)} ${symbol}</div>
  `;
  hist.prepend(hrow);
  
  // Keep only last 20 history items
  const historyItems = hist.children;
  if (historyItems.length > 20) {
    hist.removeChild(historyItems[historyItems.length - 1]);
  }
}

// Fill watchlist and history
function initAux(){
  const wl = document.getElementById('watchlist');
  markets.slice(0,4).forEach(m=>{
    const d = document.createElement('div'); 
    d.className='flex items-center justify-between'; 
    d.innerHTML = `<div>${m.symbol}</div><div class="text-slate-400">₹${fmt(m.price)}</div>`; 
    wl.appendChild(d);
  });

  // initial history
  const hist = document.getElementById('history');
  for(let i=0;i<6;i++){ 
    const hrow = document.createElement('div'); 
    hrow.className='flex items-center justify-between text-sm text-slate-300'; 
    hrow.innerHTML = `<div class="text-xs text-slate-400">${new Date(Date.now()-i*60000).toLocaleTimeString()}</div><div>${i%2?'+':'-'}${(Math.random()*2).toFixed(3)} ${markets[i%markets.length].symbol}</div>`; 
    hist.appendChild(hrow);
  }    
}

// Enhanced initialization with WebSocket support
(async function(){
  try {
    // Initialize WebSocket connection first
    console.log('Initializing BSE Trading Application...');
    
    // Load initial stock data
    await loadBSEStocks();
    
    // Set up UI components
    setupTradeForm();
    initAux();
    renderPortfolio();
    
    // Start real-time updates
    startLive();

    const marketDropdownButton = document.getElementById('market-dropdown-button');
    const marketDropdownPanel = document.getElementById('market-dropdown-panel');
    const marketList = document.getElementById('market-list');

    const searchInput = document.getElementById('search-market');
    searchInput.addEventListener('input', (event) => {
        const searchTerm = event.target.value.toLowerCase();
        const filteredMarkets = markets.filter(market => {
            return market.name.toLowerCase().includes(searchTerm) || market.symbol.toLowerCase().includes(searchTerm);
        });
        renderMarkets(filteredMarkets);
    });

    marketDropdownButton.addEventListener('click', () => {
        marketDropdownPanel.classList.toggle('hidden');
    });

    marketList.addEventListener('click', (event) => {
        const marketRow = event.target.closest('.market-row');
        if (marketRow) {
            const selectedIndex = marketRow.dataset.marketIndex;
            selectMarket(selectedIndex);
            marketDropdownPanel.classList.add('hidden');
            marketDropdownButton.textContent = markets[selectedIndex].name;
        }
    });

    document.addEventListener('click', (event) => {
        if (!marketDropdownButton.contains(event.target) && !marketDropdownPanel.contains(event.target)) {
            marketDropdownPanel.classList.add('hidden');
        }
    });

    const quickBuyButton = document.getElementById('quick-buy-button');
    const quickSellButton = document.getElementById('quick-sell-button');
    const priceInput = document.getElementById('price');
    const amountInput = document.getElementById('amount');
    const buySideButton = document.querySelector('[data-side="buy"]');
    const sellSideButton = document.querySelector('[data-side="sell"]');

    quickBuyButton.addEventListener('click', () => {
        if (selected) {
            buySideButton.click();
            priceInput.value = selected.price.toFixed(2);
            amountInput.focus();
        }
    });

    quickSellButton.addEventListener('click', () => {
        if (selected) {
            sellSideButton.click();
            priceInput.value = selected.price.toFixed(2);
            amountInput.focus();
        }
    });

    const timeframeSelector = document.getElementById('timeframe');
    timeframeSelector.addEventListener('change', (event) => {
        if (selected) {
            const timeframe = event.target.value;
            fetchHistoricalData(selected.symbol, timeframe);
        }
    });
    
    // Add window event listeners for cleanup
    window.addEventListener('beforeunload', () => {
      wsManager.disconnect();
      if (window.fallbackPollInterval) {
        clearInterval(window.fallbackPollInterval);
      }
    });
    
    // Add visibility change handler to manage connections
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) {
        // Page is hidden, reduce update frequency
        console.log('Page hidden, reducing update frequency');
      } else {
        // Page is visible, ensure connection is active
        console.log('Page visible, ensuring connection is active');
        if (!wsManager.isConnected) {
          wsManager.connect();
        }
      }
    });
    
    console.log('BSE Trading Application initialized successfully');
    
  } catch (error) {
    console.error('Failed to initialize application:', error);
    showConnectionError('Application initialization failed');
  }
})();

// Add keyboard shortcuts for trading
document.addEventListener('keydown', (event) => {
  // Ctrl+B for quick buy
  if (event.ctrlKey && event.key === 'b') {
    event.preventDefault();
    document.getElementById('submitBuy').click();
  }
  
  // Ctrl+S for quick sell
  if (event.ctrlKey && event.key === 's') {
    event.preventDefault();
    document.getElementById('submitSell').click();
  }
  
  // Escape to clear form
  if (event.key === 'Escape') {
    document.getElementById('price').value = '';
    document.getElementById('amount').value = '';
    document.getElementById('estValue').innerText = '₹0.00';
  }
});

if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        placeOrder,
        setSelected: (newSelected) => { selected = newSelected; },
        getPortfolio: () => portfolio,
        clearPortfolio: () => { portfolio = {}; },
    };
}


// Add performance metrics display
function showPerformanceMetrics() {
  const metrics = perfMonitor.getMetrics();
  const metricsEl = document.getElementById('performance-metrics') || createPerformanceMetrics();
  
  metricsEl.innerHTML = `
    <div class="text-xs text-slate-400 space-y-1">
      <div>Connection: ${metrics.connectionTime.toFixed(0)}ms</div>
      <div>Avg Latency: ${metrics.averageLatency.toFixed(0)}ms</div>
      <div>Messages: ${metrics.totalMessages}</div>
      <div>Errors: ${metrics.errorCount}</div>
    </div>
  `;
}

function createPerformanceMetrics() {
  const header = document.querySelector('header .flex.items-center.gap-3');
  const metricsEl = document.createElement('div');
  metricsEl.id = 'performance-metrics';
  metricsEl.className = 'performance-metrics text-sm px-3 py-2 rounded-lg glass';
  header.appendChild(metricsEl);
  return metricsEl;
}

// Update performance metrics every 5 seconds
setInterval(showPerformanceMetrics, 5000);

// Add connection quality indicator
function updateConnectionQuality() {
  const metrics = perfMonitor.getMetrics();
  const qualityEl = document.getElementById('connection-quality') || createConnectionQuality();
  
  let quality = 'excellent';
  let color = 'text-green-300';
  
  if (metrics.averageLatency > 1000 || metrics.errorRate > 5) {
    quality = 'poor';
    color = 'text-red-300';
  } else if (metrics.averageLatency > 500 || metrics.errorRate > 2) {
    quality = 'fair';
    color = 'text-yellow-300';
  } else if (metrics.averageLatency > 200) {
    quality = 'good';
    color = 'text-blue-300';
  }
  
  qualityEl.className = `connection-quality text-xs ${color}`;
  qualityEl.textContent = quality;
}

function createConnectionQuality() {
  const statusEl = document.querySelector('.connection-status');
  if (statusEl) {
    const qualityEl = document.createElement('div');
    qualityEl.id = 'connection-quality';
    statusEl.appendChild(qualityEl);
    return qualityEl;
  }
  return null;
}

// Update connection quality every 10 seconds
setInterval(updateConnectionQuality, 10000);

// Enhanced error and message handling
function showErrorMessage(message, duration = 5000) {
  showMessage(message, 'error', duration);
}

function showWarningMessage(message, duration = 5000) {
  showMessage(message, 'warning', duration);
}

function showSuccessMessage(message, duration = 3000) {
  showMessage(message, 'success', duration);
}

function showMessage(message, type = 'info', duration = 3000) {
  // Remove existing messages
  const existingMessages = document.querySelectorAll('.toast-message');
  existingMessages.forEach(msg => msg.remove());
  
  const toast = document.createElement('div');
  toast.className = `toast-message fixed top-4 right-4 z-50 p-4 rounded-lg shadow-lg max-w-sm transition-all duration-300 transform translate-x-full`;
  
  const colors = {
    error: 'bg-red-900/90 text-red-100 border border-red-700',
    warning: 'bg-yellow-900/90 text-yellow-100 border border-yellow-700',
    success: 'bg-green-900/90 text-green-100 border border-green-700',
    info: 'bg-blue-900/90 text-blue-100 border border-blue-700'
  };
  
  toast.className += ` ${colors[type] || colors.info}`;
  toast.innerHTML = `
    <div class="flex items-start gap-3">
      <div class="flex-1">
        <div class="font-medium text-sm">${message}</div>
      </div>
      <button class="text-current opacity-70 hover:opacity-100" onclick="this.parentElement.parentElement.remove()">
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"></path>
        </svg>
      </button>
    </div>
  `;
  
  document.body.appendChild(toast);
  
  // Animate in
  requestAnimationFrame(() => {
    toast.classList.remove('translate-x-full');
  });
  
  // Auto remove after duration
  if (duration > 0) {
    setTimeout(() => {
      toast.classList.add('translate-x-full');
      setTimeout(() => toast.remove(), 300);
    }, duration);
  }
}

// Enhanced market initialization with performance optimization
async function initializeMarkets() {
  const marketContainer = document.getElementById('market-list');
  if (!marketContainer) return;
  
  // Show loading state for market list
  perfOptimizer.setLoadingState('market-list', true, 'Initializing markets...');
  
  try {
    // Get initial market data with batch processing
    const symbols = Object.keys(bseStocks).slice(0, 20); // Limit to first 20 for performance
    
    console.log(`Initializing markets with ${symbols.length} symbols:`, symbols);
    
    // Try batch fetch first, fallback to individual quotes, then mock data
    let marketData = {};
    
    try {
      marketData = await fetchBatchMarketData(symbols);
      console.log('Batch market data fetched:', marketData);
    } catch (batchError) {
      console.warn('Batch fetch failed, trying individual quotes:', batchError);
      
      // Fallback to individual quotes for first few stocks
      for (const symbol of symbols.slice(0, 5)) {
        try {
          const quote = await fetchSingleQuote(symbol);
          if (quote) {
            marketData[symbol] = quote;
          }
        } catch (quoteError) {
          console.warn(`Failed to fetch quote for ${symbol}:`, quoteError);
        }
      }
    }
    
    // If still no data, create mock data for demonstration
    if (Object.keys(marketData).length === 0) {
      console.log('Creating mock market data for demonstration');
      marketData = createMockMarketData(symbols);
    }
    
    // Process market data efficiently
    markets = symbols.map(symbol => ({
      symbol,
      name: bseStocks[symbol],
      price: marketData[symbol]?.price || (1000 + Math.random() * 2000),
      change: marketData[symbol]?.change || ((Math.random() - 0.5) * 100),
      pChange: marketData[symbol]?.pChange || ((Math.random() - 0.5) * 10),
      volume: marketData[symbol]?.volume || Math.floor(Math.random() * 1000000),
      lastUpdate: Date.now()
    }));
    
    // Cache market data
    localStorage.setItem('bse_stocks_cache', JSON.stringify(bseStocks));
    localStorage.setItem('markets_cache', JSON.stringify(markets));
    
    // Render markets with performance optimization
    renderMarkets(markets);
    
    // Select first stock by default
    if (markets.length > 0) {
      selectStock(markets[0]);
    }
    
    // Clear loading state
    perfOptimizer.setLoadingState('market-list', false);
    
    showSuccessMessage(`Loaded ${markets.length} stocks successfully`);
    
  } catch (error) {
    console.error('Failed to initialize markets:', error);
    perfOptimizer.setLoadingState('market-list', false);
    showErrorMessage('Failed to initialize market data');
  }
}

// Fetch single stock quote
async function fetchSingleQuote(symbol) {
  try {
    const response = await fetch(`http://localhost:3002/api/quote/${symbol}`);
    
    if (!response.ok) {
      throw new Error(`Quote fetch failed: ${response.status}`);
    }
    
    const data = await response.json();
    
    // Handle different response formats
    if (data.price !== undefined) {
      return {
        price: parseFloat(data.price),
        change: parseFloat(data.change || 0),
        pChange: parseFloat(data.pChange || 0),
        volume: parseInt(data.volume || 0)
      };
    } else if (data.current_price !== undefined) {
      return {
        price: parseFloat(data.current_price),
        change: parseFloat(data.change || 0),
        pChange: parseFloat(data.percent_change || 0),
        volume: parseInt(data.volume || 0)
      };
    }
    
    return null;
  } catch (error) {
    console.error(`Failed to fetch quote for ${symbol}:`, error);
    return null;
  }
}

// Create mock market data for demonstration
function createMockMarketData(symbols) {
  const mockData = {};
  
  symbols.forEach((symbol, index) => {
    // Create realistic-looking mock data
    const basePrice = 500 + (index * 100) + Math.random() * 500;
    const change = (Math.random() - 0.5) * 50;
    const pChange = (change / basePrice) * 100;
    
    mockData[symbol] = {
      price: parseFloat(basePrice.toFixed(2)),
      change: parseFloat(change.toFixed(2)),
      pChange: parseFloat(pChange.toFixed(2)),
      volume: Math.floor(Math.random() * 1000000) + 10000
    };
  });
  
  return mockData;
}

// Batch market data fetching with error handling
async function fetchBatchMarketData(symbols) {
  try {
    // Try the v2 API first
    const response = await fetch('http://localhost:3002/api/v2/quotes', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: JSON.stringify({ symbols })
    });
    
    if (!response.ok) {
      throw new Error(`Batch fetch failed: ${response.status}`);
    }
    
    const responseData = await response.json();
    
    // Handle v2 API response format
    if (responseData.successful_quotes) {
      const validatedData = {};
      
      Object.entries(responseData.successful_quotes).forEach(([symbol, data]) => {
        validatedData[symbol] = {
          price: parseFloat(data.current_price || data.price || 0),
          change: parseFloat(data.change || 0),
          pChange: parseFloat(data.percent_change || data.pChange || 0),
          volume: parseInt(data.volume || 0)
        };
      });
      
      return validatedData;
    }
    
    throw new Error('Invalid batch response format');
    
  } catch (error) {
    console.error('Batch market data fetch failed:', error);
    throw error; // Re-throw to trigger fallback
  }
}

// Enhanced DOM update optimization for market rendering


// Optimized market row creation with event delegation
function createMarketRow(market, index) {
  const row = document.createElement('div');
  row.className = 'market-row flex items-center justify-between p-3 rounded-lg glass hover:bg-slate-800/30 cursor-pointer transition-all duration-200';
  row.dataset.symbol = market.symbol;
  row.dataset.index = index;
  
  const isPositive = market.pChange >= 0;
  const changeColor = isPositive ? 'text-green-300' : 'text-red-300';
  const changeBg = isPositive ? 'bg-green-900/20' : 'bg-red-900/20';
  
  // Check for stale data
  const isStale = Date.now() - market.lastUpdate > 30000; // 30 seconds
  const staleClass = isStale ? 'stale-data' : '';
  
  row.innerHTML = `
    <div class="flex-1 ${staleClass}">
      <div class="font-medium text-sm">${market.name}</div>
      <div class="text-xs text-slate-400">${market.symbol}</div>
    </div>
    <div class="text-right">
      <div class="font-medium">₹${fmt(market.price)}</div>
      <div class="text-xs ${changeColor} ${changeBg} px-2 py-1 rounded">
        ${isPositive ? '+' : ''}${market.pChange.toFixed(2)}%
      </div>
    </div>
  `;
  
  // Add click handler with performance optimization
  row.addEventListener('click', (e) => {
    e.preventDefault();
    selectStock(market);
  });
  
  return row;
}

// Enhanced stock selection with validation and error handling
function selectStock(stock) {
  if (!stock || !DataValidator.validateStockData(stock)) {
    showErrorMessage('Invalid stock data');
    return;
  }
  
  // Update selected stock
  selected = { ...stock };
  
  // Subscribe to real-time updates
  if (wsManager.isConnected) {
    wsManager.subscribe(stock.symbol);
  }
  
  // Update UI with performance optimization
  updateSelectedStockUI();
  
  // Load historical data for chart
  loadStockChart(stock.symbol);
  
  // Update order book
  loadOrderBook(stock.symbol);
  
  // Highlight selected row
  highlightSelectedRow(stock.symbol);
}

// Optimized UI update for selected stock
function updateSelectedStockUI() {
  if (!selected) return;
  
  const isPositive = selected.pChange >= 0;
  
  // Batch all UI updates
  perfOptimizer.queueDOMUpdate('selected-stock-ui', () => {
    // Update symbol and name
    const symbolEl = document.getElementById('selected-symbol');
    if (symbolEl) {
      symbolEl.textContent = selected.name || selected.symbol;
    }
    
    // Update price with animation
    const priceEl = document.getElementById('selected-price');
    if (priceEl) {
      const oldPrice = parseFloat(priceEl.textContent.replace('₹', '').replace(/,/g, '')) || 0;
      priceEl.textContent = '₹' + fmt(selected.price);
      
      if (Math.abs(selected.price - oldPrice) > 0.01) {
        perfOptimizer.animatePriceChange('selected-price', selected.price, oldPrice);
      }
    }
    
    // Update change indicator
    const changeEl = document.getElementById('selected-change');
    if (changeEl) {
      changeEl.textContent = (isPositive ? '+' : '') + selected.pChange.toFixed(2) + '%';
      changeEl.className = `text-sm px-2 py-1 rounded-md transition-all duration-300 ${
        isPositive ? 'bg-green-900/30 text-green-300' : 'bg-red-900/30 text-red-300'
      }`;
    }
  });
}

// Enhanced chart loading with error handling and optimization
async function loadStockChart(symbol) {
  if (!symbol) return;
  
  try {
    // Show loading state for chart
    const chartContainer = document.getElementById('mainChart').parentElement;
    perfOptimizer.setLoadingState('chart-container', true, 'Loading chart data...');
    
    // Fetch historical data
    const response = await fetch(`http://localhost:3002/api/historical/${symbol}?timeframe=1d&limit=100`);
    
    if (!response.ok) {
      throw new Error(`Chart data fetch failed: ${response.status}`);
    }
    
    const historicalData = await response.json();
    
    // Validate historical data
    if (!Array.isArray(historicalData) || historicalData.length === 0) {
      throw new Error('Invalid historical data format');
    }
    
    // Initialize or update chart
    initializeChart(historicalData);
    
    perfOptimizer.setLoadingState('chart-container', false);
    
  } catch (error) {
    console.error('Failed to load chart data:', error);
    perfOptimizer.setLoadingState('chart-container', false);
    
    // Initialize chart with mock data
    const mockData = generateMockHistoricalData(symbol);
    initializeChart(mockData);
    
    showWarningMessage('Using simulated chart data');
  }
}

// Generate mock historical data for development/testing
function generateMockHistoricalData(symbol) {
  const data = [];
  const basePrice = selected?.price || 1000;
  const now = new Date();
  
  for (let i = 99; i >= 0; i--) {
    const timestamp = new Date(now.getTime() - i * 60000); // 1 minute intervals
    const price = basePrice + (Math.random() - 0.5) * basePrice * 0.1; // ±10% variation
    
    data.push({
      timestamp: timestamp.toISOString(),
      price: price,
      volume: Math.floor(Math.random() * 10000)
    });
  }
  
  return data;
}

// Enhanced chart initialization with performance optimization
function initializeChart(historicalData) {
  const ctx = document.getElementById('mainChart');
  if (!ctx) return;
  
  // Destroy existing chart
  if (chart) {
    chart.destroy();
  }
  
  // Prepare chart data with optimization
  const labels = historicalData.map(d => {
    const date = new Date(d.timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  });
  
  const prices = historicalData.map(d => parseFloat(d.price));
  
  // Create optimized chart configuration
  const config = {
    type: 'line',
    data: {
      labels: labels,
      datasets: [{
        label: selected?.name || 'Price',
        data: prices,
        borderColor: '#6366f1',
        backgroundColor: 'rgba(99, 102, 241, 0.1)',
        borderWidth: 2,
        fill: true,
        tension: 0.1,
        pointRadius: 0, // Hide points for better performance
        pointHoverRadius: 4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        intersect: false,
        mode: 'index'
      },
      plugins: {
        legend: {
          display: false
        },
        tooltip: {
          backgroundColor: 'rgba(0, 0, 0, 0.8)',
          titleColor: '#e2e8f0',
          bodyColor: '#e2e8f0',
          borderColor: '#475569',
          borderWidth: 1
        }
      },
      scales: {
        x: {
          display: true,
          grid: {
            color: 'rgba(148, 163, 184, 0.1)'
          },
          ticks: {
            color: '#94a3b8',
            maxTicksLimit: 8
          }
        },
        y: {
          display: true,
          grid: {
            color: 'rgba(148, 163, 184, 0.1)'
          },
          ticks: {
            color: '#94a3b8',
            callback: function(value) {
              return '₹' + value.toFixed(2);
            }
          }
        }
      },
      animation: {
        duration: 300 // Reduced animation duration for better performance
      }
    }
  };
  
  // Create chart with error handling
  try {
    chart = new Chart(ctx, config);
  } catch (error) {
    console.error('Failed to create chart:', error);
    showErrorMessage('Chart initialization failed');
  }
}

// Enhanced order book loading with validation
async function loadOrderBook(symbol) {
  if (!symbol) return;
  
  try {
    const response = await fetch(`http://localhost:3002/api/orderbook/${symbol}`);
    
    if (!response.ok) {
      throw new Error(`Order book fetch failed: ${response.status}`);
    }
    
    const orderBook = await response.json();
    
    // Validate order book data
    if (!orderBook || !orderBook.bids || !orderBook.asks) {
      throw new Error('Invalid order book format');
    }
    
    renderOrderBook(orderBook);
    
  } catch (error) {
    console.error('Failed to load order book:', error);
    
    // Generate mock order book
    const mockOrderBook = generateMockOrderBook();
    renderOrderBook(mockOrderBook);
  }
}

// Generate mock order book for development/testing
function generateMockOrderBook() {
  const basePrice = selected?.price || 1000;
  const bids = [];
  const asks = [];
  
  // Generate bids (buy orders) - prices below current price
  for (let i = 0; i < 5; i++) {
    bids.push({
      price: basePrice - (i + 1) * 0.5,
      quantity: Math.floor(Math.random() * 1000) + 100,
      orders: Math.floor(Math.random() * 10) + 1
    });
  }
  
  // Generate asks (sell orders) - prices above current price
  for (let i = 0; i < 5; i++) {
    asks.push({
      price: basePrice + (i + 1) * 0.5,
      quantity: Math.floor(Math.random() * 1000) + 100,
      orders: Math.floor(Math.random() * 10) + 1
    });
  }
  
  return { bids, asks };
}

// Optimized order book rendering


// Highlight selected market row
function highlightSelectedRow(symbol) {
  // Remove previous selection
  document.querySelectorAll('.market-row').forEach(row => {
    row.classList.remove('bg-indigo-900/30', 'border-indigo-500/50');
  });
  
  // Highlight current selection
  const selectedRow = document.querySelector(`[data-symbol="${symbol}"]`);
  if (selectedRow) {
    selectedRow.classList.add('bg-indigo-900/30', 'border-indigo-500/50');
  }
}

// Enhanced form validation with real-time feedback


// Enhanced order submission with validation and error handling
async function submitOrder(side) {
  const priceInput = document.getElementById('price');
  const amountInput = document.getElementById('amount');
  
  if (!priceInput || !amountInput || !selected) {
    showErrorMessage('Please select a stock and enter order details');
    return;
  }
  
  // Validate inputs
  const priceValid = perfOptimizer.validateField('price', priceInput.value);
  const amountValid = perfOptimizer.validateField('amount', amountInput.value);
  
  if (!priceValid || !amountValid || perfOptimizer.hasValidationErrors()) {
    showErrorMessage('Please fix validation errors before submitting');
    return;
  }
  
  const orderData = {
    symbol: selected.symbol,
    side: side,
    price: parseFloat(priceInput.value),
    amount: parseFloat(amountInput.value),
    timestamp: new Date().toISOString()
  };
  
  // Validate order data
  const validation = DataValidator.validateOrderData(orderData);
  if (!validation.valid) {
    showErrorMessage('Invalid order data: ' + validation.errors.join(', '));
    return;
  }
  
  // Show loading state
  const submitButton = document.getElementById(side === 'buy' ? 'submitBuy' : 'submitSell');
  if (submitButton) {
    submitButton.disabled = true;
    submitButton.textContent = 'Submitting...';
  }
  
  try {
    const response = await fetch('http://localhost:3002/api/orders', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: JSON.stringify(orderData)
    });
    
    if (!response.ok) {
      throw new Error(`Order submission failed: ${response.status}`);
    }
    
    const result = await response.json();
    
    showSuccessMessage(`${side.toUpperCase()} order submitted successfully`);
    
    // Clear form
    priceInput.value = '';
    amountInput.value = '';
    document.getElementById('estValue').textContent = '₹0.00';
    
    // Update open orders
    updateOpenOrders();
    
  } catch (error) {
    console.error('Order submission failed:', error);
    showErrorMessage('Failed to submit order. Please try again.');
  } finally {
    // Restore button state
    if (submitButton) {
      submitButton.disabled = false;
      submitButton.textContent = side === 'buy' ? 'Place Buy' : 'Place Sell';
    }
  }
}

// Update open orders display
async function updateOpenOrders() {
  try {
    const response = await fetch('http://localhost:3002/api/orders');
    
    if (!response.ok) {
      throw new Error(`Failed to fetch orders: ${response.status}`);
    }
    
    const orders = await response.json();
    renderOpenOrders(orders);
    
  } catch (error) {
    console.error('Failed to update open orders:', error);
    // Show mock orders for development
    renderOpenOrders([]);
  }
}

// Render open orders with performance optimization
function renderOpenOrders(orders) {
  const container = document.getElementById('openOrders');
  if (!container) return;
  
  if (!orders || orders.length === 0) {
    container.innerHTML = '<div class="text-slate-400 text-xs">No open orders</div>';
    return;
  }
  
  perfOptimizer.queueDOMUpdate('open-orders', () => {
    container.innerHTML = orders.map(order => `
      <div class="flex justify-between items-center p-2 rounded bg-slate-800/30" data-order-id="${order.id}">
        <div class="flex-1">
          <div class="text-xs font-medium">${order.symbol}</div>
          <div class="text-xs text-slate-400">${order.side.toUpperCase()} ${order.amount}</div>
        </div>
        <div class="text-right">
          <div class="text-xs">₹${order.price.toFixed(2)}</div>
          <div class="order-status text-xs ${
            order.status === 'filled' ? 'text-green-300' :
            order.status === 'cancelled' ? 'text-red-300' :
            'text-yellow-300'
          }">${order.status}</div>
        </div>
      </div>
    `).join('');
  });
}

// Initialize WebSocket connection with enhanced error handling
function initializeWebSocket() {
  // Set up WebSocket callbacks
  wsManager.onConnected = () => {
    console.log('WebSocket connected successfully');
    showSuccessMessage('Real-time connection established');
    
    // Subscribe to selected stock if any
    if (selected) {
      wsManager.subscribe(selected.symbol);
    }
  };
  
  wsManager.onDisconnected = () => {
    console.log('WebSocket disconnected');
    showWarningMessage('Real-time connection lost. Attempting to reconnect...');
  };
  
  wsManager.onStockUpdate = (data) => {
    // Handle real-time stock updates
    console.log('Received stock update:', data);
  };
  
  wsManager.onOrderUpdate = (data) => {
    // Handle real-time order updates
    console.log('Received order update:', data);
    updateOpenOrders();
  };
  
  // Connect to WebSocket
  wsManager.connect();
}



// Initialize application with error handling
async function initializeApp() {
  try {
    console.log('Initializing BSE Trading Application...');
    
    // Load stocks and initialize markets
    const stocksLoaded = await loadBSEStocks();
    
    if (!stocksLoaded) {
      showErrorMessage('Failed to load market data. Some features may not work properly.');
    }
    
    // Setup form validation
    setupFormValidation();
    
    // Initialize WebSocket connection
    initializeWebSocket();
    
    // Setup event listeners
    setupEventListeners();
    
    // Update open orders
    updateOpenOrders();
    
    console.log('Application initialized successfully');
    
  } catch (error) {
    console.error('Application initialization failed:', error);
    showErrorMessage('Application failed to initialize. Please refresh the page.');
  }
}

// Setup event listeners with performance optimization
function setupEventListeners() {
  // Order submission buttons
  const buyButton = document.getElementById('submitBuy');
  const sellButton = document.getElementById('submitSell');
  
  if (buyButton) {
    buyButton.addEventListener('click', (e) => {
      e.preventDefault();
      submitOrder('buy');
    });
  }
  
  if (sellButton) {
    sellButton.addEventListener('click', (e) => {
      e.preventDefault();
      submitOrder('sell');
    });
  }
  
  // Side selection buttons
  document.querySelectorAll('[data-side]').forEach(button => {
    button.addEventListener('click', (e) => {
      e.preventDefault();
      const side = button.dataset.side;
      
      // Update button states
      document.querySelectorAll('[data-side]').forEach(btn => {
        btn.classList.remove('bg-green-600/30', 'bg-red-600/30');
        btn.classList.add(btn.dataset.side === 'buy' ? 'bg-green-600/10' : 'bg-red-600/10');
      });
      
      // Highlight selected side
      button.classList.remove('bg-green-600/10', 'bg-red-600/10');
      button.classList.add(side === 'buy' ? 'bg-green-600/30' : 'bg-red-600/30');
    });
  });
  
  // Timeframe selector
  const timeframeSelect = document.getElementById('timeframe');
  if (timeframeSelect) {
    timeframeSelect.addEventListener('change', (e) => {
      if (selected) {
        loadStockChart(selected.symbol);
      }
    });
  }
  
  // Keyboard shortcuts
  document.addEventListener('keydown', (e) => {
    // Ctrl+R: Refresh data
    if (e.ctrlKey && e.key === 'r') {
      e.preventDefault();
      location.reload();
    }
    
    // Escape: Clear form
    if (e.key === 'Escape') {
      const priceInput = document.getElementById('price');
      const amountInput = document.getElementById('amount');
      if (priceInput) priceInput.value = '';
      if (amountInput) amountInput.value = '';
    }
  });
}

// Debug function to test data loading
async function debugDataLoading() {
  console.log('🔍 Debug: Testing data loading...');
  
  try {
    // Test backend connection
    const healthResponse = await fetch('http://localhost:3002/health');
    console.log('✅ Backend health check:', healthResponse.status);
    
    // Test stocks endpoint
    const stocksResponse = await fetch('http://localhost:3002/api/stocks');
    const stocksData = await stocksResponse.json();
    console.log('📊 Stocks data received:', stocksData);
    
    // Test single quote
    const quoteResponse = await fetch('http://localhost:3002/api/quote/500325');
    const quoteData = await quoteResponse.json();
    console.log('💰 Quote data received:', quoteData);
    
  } catch (error) {
    console.error('❌ Debug test failed:', error);
  }
}

// Enhanced initialization with debugging
async function initializeAppWithDebug() {
  console.log('🚀 Starting BSE Trading Application with debugging...');
  
  // Run debug test first
  await debugDataLoading();
  
  // Then run normal initialization
  await initializeApp();
}

// Start the application when DOM is loaded
document.addEventListener('DOMContentLoaded', initializeAppWithDebug);