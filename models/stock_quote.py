from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import json


@dataclass
class StockQuote:
    """Data model for stock quote information with serialization support."""
    
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
    
    def to_dict(self) -> dict:
        """Convert StockQuote to dictionary for serialization."""
        return {
            'symbol': self.symbol,
            'company_name': self.company_name,
            'current_price': self.current_price,
            'change': self.change,
            'percent_change': self.percent_change,
            'volume': self.volume,
            'timestamp': self.timestamp.isoformat(),
            'bid_price': self.bid_price,
            'ask_price': self.ask_price,
            'high': self.high,
            'low': self.low
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'StockQuote':
        """Create StockQuote from dictionary."""
        # Parse timestamp back to datetime object
        timestamp = datetime.fromisoformat(data['timestamp'])
        
        return cls(
            symbol=data['symbol'],
            company_name=data['company_name'],
            current_price=data['current_price'],
            change=data['change'],
            percent_change=data['percent_change'],
            volume=data['volume'],
            timestamp=timestamp,
            bid_price=data.get('bid_price'),
            ask_price=data.get('ask_price'),
            high=data.get('high'),
            low=data.get('low')
        )
    
    def to_json(self) -> str:
        """Convert StockQuote to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'StockQuote':
        """Create StockQuote from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def to_redis_value(self) -> str:
        """Convert to Redis-compatible string value."""
        return self.to_json()
    
    @classmethod
    def from_redis_value(cls, redis_value: str) -> 'StockQuote':
        """Create StockQuote from Redis string value."""
        return cls.from_json(redis_value)