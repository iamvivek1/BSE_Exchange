# services/compression_service.py
import msgpack
import json
import gzip
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
import logging
from models.stock_quote import StockQuote

logger = logging.getLogger(__name__)

class CompressionService:
    """
    Service for data compression and optimization to minimize bandwidth usage
    for real-time stock data updates.
    """
    
    def __init__(self):
        self.previous_data_cache: Dict[str, Dict] = {}  # symbol -> last data
        self.compression_stats = {
            'total_compressions': 0,
            'total_original_size': 0,
            'total_compressed_size': 0,
            'delta_updates': 0,
            'full_updates': 0
        }
    
    def compress_stock_data(self, data: Union[Dict, StockQuote], use_gzip: bool = False) -> bytes:
        """
        Compress stock data using MessagePack with optional gzip compression.
        
        Args:
            data: Stock data as dictionary or StockQuote object
            use_gzip: Whether to apply additional gzip compression
            
        Returns:
            Compressed data as bytes
        """
        try:
            # Convert StockQuote to dict if needed
            if isinstance(data, StockQuote):
                data_dict = data.to_dict()
            else:
                data_dict = data
            
            # Optimize data structure for compression
            optimized_data = self._optimize_data_structure(data_dict)
            
            # Serialize with MessagePack
            packed_data = msgpack.packb(optimized_data, use_bin_type=True)
            
            # Apply gzip compression if requested
            if use_gzip:
                packed_data = gzip.compress(packed_data)
            
            # Update compression stats
            original_size = len(json.dumps(data_dict).encode('utf-8'))
            compressed_size = len(packed_data)
            
            self.compression_stats['total_compressions'] += 1
            self.compression_stats['total_original_size'] += original_size
            self.compression_stats['total_compressed_size'] += compressed_size
            
            logger.debug(f"Compressed data: {original_size} -> {compressed_size} bytes "
                        f"({(1 - compressed_size/original_size)*100:.1f}% reduction)")
            
            return packed_data
            
        except Exception as e:
            logger.error(f"Failed to compress stock data: {e}")
            # Fallback to JSON encoding with error handling
            try:
                fallback_data = data_dict if isinstance(data, dict) else data.to_dict()
                return json.dumps(fallback_data).encode('utf-8')
            except (TypeError, ValueError) as json_error:
                logger.error(f"JSON fallback also failed: {json_error}")
                # Return minimal error response
                error_response = {
                    'error': 'compression_failed',
                    'message': str(e),
                    'timestamp': datetime.now().isoformat()
                }
                return json.dumps(error_response).encode('utf-8')
    
    def decompress_stock_data(self, compressed_data: bytes, use_gzip: bool = False) -> Dict[str, Any]:
        """
        Decompress stock data from MessagePack format.
        
        Args:
            compressed_data: Compressed data as bytes
            use_gzip: Whether the data was gzip compressed
            
        Returns:
            Decompressed data as dictionary
        """
        try:
            # Decompress gzip if needed
            if use_gzip:
                compressed_data = gzip.decompress(compressed_data)
            
            # Unpack MessagePack data
            unpacked_data = msgpack.unpackb(compressed_data, raw=False)
            
            # Restore optimized data structure
            restored_data = self._restore_data_structure(unpacked_data)
            
            return restored_data
            
        except Exception as e:
            logger.error(f"Failed to decompress stock data: {e}")
            # Fallback to JSON decoding
            try:
                return json.loads(compressed_data.decode('utf-8'))
            except:
                raise ValueError(f"Unable to decompress data: {e}")
    
    def create_delta_update(self, symbol: str, new_data: Union[Dict, StockQuote]) -> Dict[str, Any]:
        """
        Create a delta update containing only changed fields.
        
        Args:
            symbol: Stock symbol
            new_data: New stock data
            
        Returns:
            Delta update dictionary with only changed fields
        """
        # Convert StockQuote to dict if needed
        if isinstance(new_data, StockQuote):
            new_dict = new_data.to_dict()
        else:
            new_dict = new_data.copy()
        
        # Get previous data for this symbol
        previous_data = self.previous_data_cache.get(symbol, {})
        
        # Create delta update
        delta = {
            'symbol': symbol,
            'type': 'delta',
            'timestamp': new_dict.get('timestamp', datetime.now().isoformat()),
            'changes': {}
        }
        
        # Compare fields and include only changes
        for key, new_value in new_dict.items():
            if key == 'timestamp':
                # Always include timestamp
                delta['timestamp'] = new_value
                continue
                
            old_value = previous_data.get(key)
            
            # Include field if it's new or changed
            if old_value != new_value:
                delta['changes'][key] = new_value
        
        # Cache the new data for future delta calculations
        self.previous_data_cache[symbol] = new_dict.copy()
        
        # Update stats
        if delta['changes']:
            self.compression_stats['delta_updates'] += 1
            logger.debug(f"Created delta update for {symbol} with {len(delta['changes'])} changes")
        else:
            # No changes, return minimal update
            delta = {
                'symbol': symbol,
                'type': 'heartbeat',
                'timestamp': new_dict.get('timestamp', datetime.now().isoformat())
            }
        
        return delta
    
    def create_full_update(self, symbol: str, data: Union[Dict, StockQuote]) -> Dict[str, Any]:
        """
        Create a full update with all stock data.
        
        Args:
            symbol: Stock symbol
            data: Complete stock data
            
        Returns:
            Full update dictionary
        """
        # Convert StockQuote to dict if needed
        if isinstance(data, StockQuote):
            data_dict = data.to_dict()
        else:
            data_dict = data.copy()
        
        full_update = {
            'symbol': symbol,
            'type': 'full',
            'timestamp': data_dict.get('timestamp', datetime.now().isoformat()),
            'data': data_dict
        }
        
        # Cache the data for future delta calculations
        self.previous_data_cache[symbol] = data_dict.copy()
        
        # Update stats
        self.compression_stats['full_updates'] += 1
        
        return full_update
    
    def compress_batch_updates(self, updates: List[Dict]) -> bytes:
        """
        Compress multiple stock updates together for better compression ratio.
        
        Args:
            updates: List of stock update dictionaries
            
        Returns:
            Compressed batch data as bytes
        """
        try:
            # Optimize batch structure
            batch_data = {
                'type': 'batch',
                'timestamp': datetime.now().isoformat(),
                'count': len(updates),
                'updates': updates
            }
            
            # Use MessagePack with gzip for batch data
            return self.compress_stock_data(batch_data, use_gzip=True)
            
        except Exception as e:
            logger.error(f"Failed to compress batch updates: {e}")
            raise
    
    def decompress_batch_updates(self, compressed_batch: bytes) -> List[Dict]:
        """
        Decompress batch updates.
        
        Args:
            compressed_batch: Compressed batch data
            
        Returns:
            List of decompressed update dictionaries
        """
        try:
            batch_data = self.decompress_stock_data(compressed_batch, use_gzip=True)
            return batch_data.get('updates', [])
            
        except Exception as e:
            logger.error(f"Failed to decompress batch updates: {e}")
            raise
    
    def _optimize_data_structure(self, data: Dict) -> Dict:
        """
        Optimize data structure for better compression by using shorter keys
        and more efficient data types.
        """
        # Create mapping for common field names to shorter versions
        field_mapping = {
            'symbol': 's',
            'company_name': 'cn',
            'current_price': 'cp',
            'change': 'c',
            'percent_change': 'pc',
            'volume': 'v',
            'timestamp': 't',
            'bid_price': 'bp',
            'ask_price': 'ap',
            'high': 'h',
            'low': 'l'
        }
        
        optimized = {}
        for key, value in data.items():
            # Use shorter key if available
            short_key = field_mapping.get(key, key)
            
            # Optimize value based on type
            if isinstance(value, float):
                # Round to reasonable precision to improve compression
                if key in ['current_price', 'change', 'bid_price', 'ask_price', 'high', 'low']:
                    optimized[short_key] = round(value, 2)
                elif key == 'percent_change':
                    optimized[short_key] = round(value, 3)
                else:
                    optimized[short_key] = value
            elif value is not None:
                optimized[short_key] = value
        
        return optimized
    
    def _restore_data_structure(self, optimized_data: Dict) -> Dict:
        """
        Restore original data structure from optimized format.
        """
        # Reverse mapping for field names
        reverse_mapping = {
            's': 'symbol',
            'cn': 'company_name',
            'cp': 'current_price',
            'c': 'change',
            'pc': 'percent_change',
            'v': 'volume',
            't': 'timestamp',
            'bp': 'bid_price',
            'ap': 'ask_price',
            'h': 'high',
            'l': 'low'
        }
        
        restored = {}
        for key, value in optimized_data.items():
            # Restore original key name
            original_key = reverse_mapping.get(key, key)
            restored[original_key] = value
        
        return restored
    
    def get_compression_stats(self) -> Dict[str, Any]:
        """
        Get compression performance statistics.
        
        Returns:
            Dictionary with compression statistics
        """
        stats = self.compression_stats.copy()
        
        if stats['total_compressions'] > 0:
            stats['average_compression_ratio'] = (
                1 - stats['total_compressed_size'] / stats['total_original_size']
            ) * 100
            stats['average_original_size'] = stats['total_original_size'] / stats['total_compressions']
            stats['average_compressed_size'] = stats['total_compressed_size'] / stats['total_compressions']
        else:
            stats['average_compression_ratio'] = 0
            stats['average_original_size'] = 0
            stats['average_compressed_size'] = 0
        
        return stats
    
    def reset_stats(self):
        """Reset compression statistics."""
        self.compression_stats = {
            'total_compressions': 0,
            'total_original_size': 0,
            'total_compressed_size': 0,
            'delta_updates': 0,
            'full_updates': 0
        }
        logger.info("Compression statistics reset")
    
    def clear_cache(self):
        """Clear the previous data cache."""
        self.previous_data_cache.clear()
        logger.info("Previous data cache cleared")