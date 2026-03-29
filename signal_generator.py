from datetime import datetime
import json
from pathlib import Path
from patterns import CandlestickPatterns
from binance_client import BinanceClient
from config import SIGNALS_HISTORY_FILE, MAX_HISTORY_RECORDS, CONFIDENCE_THRESHOLD

class SignalGenerator:
    """Generates trading signals based on candlestick patterns"""
    
    def __init__(self):
        """Initialize signal generator"""
        self.binance = BinanceClient()
        self.signals_history = self._load_history()
    
    def _load_history(self):
        """Load signals history from file"""
        if Path(SIGNALS_HISTORY_FILE).exists():
            try:
                with open(SIGNALS_HISTORY_FILE, 'r') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def _save_history(self):
        """Save signals history to file"""
        # Keep only recent records
        if len(self.signals_history) > MAX_HISTORY_RECORDS:
            self.signals_history = self.signals_history[-MAX_HISTORY_RECORDS:]
        
        with open(SIGNALS_HISTORY_FILE, 'w') as f:
            json.dump(self.signals_history, f, indent=2)
    
    def generate_signals(self, symbol, interval):
        """
        Generate trading signals for a symbol
        
        Args:
            symbol: Trading pair (e.g., 'ETHUSDT')
            interval: Timeframe (e.g., '15m')
        
        Returns:
            Dictionary with signals and metadata
        """
        # Fetch historical data
        df = self.binance.get_historical_data(symbol, interval)
        
        if df is None or len(df) == 0:
            return {
                'success': False,
                'error': 'Failed to fetch data'
            }
        
        # Detect patterns
        detector = CandlestickPatterns(df)
        all_signals = detector.detect_all_patterns()
        
        # Filter by confidence threshold
        filtered_signals = [
            s for s in all_signals 
            if s['confidence'] >= CONFIDENCE_THRESHOLD
        ]
        
        # Get current price
        current_price = self.binance.get_latest_price(symbol)
        
        # Get last candle info
        last_candle = df.iloc[-1]
        
        result = {
            'success': True,
            'symbol': symbol,
            'interval': interval,
            'timestamp': datetime.now().isoformat(),
            'current_price': current_price,
            'last_candle': {
                'open': float(last_candle['open']),
                'high': float(last_candle['high']),
                'low': float(last_candle['low']),
                'close': float(last_candle['close']),
                'time': str(last_candle['open_time'])
            },
            'signals_detected': len(filtered_signals),
            'buy_signals': len([s for s in filtered_signals if s['signal'] == 'BUY']),
            'sell_signals': len([s for s in filtered_signals if s['signal'] == 'SELL']),
            'neutral_signals': len([s for s in filtered_signals if s['signal'] == 'NEUTRAL']),
            'patterns': filtered_signals
        }
        
        # Store in history
        self._store_signal(result)
        
        return result
    
    def _store_signal(self, signal_data):
        """Store signal in history"""
        self.signals_history.append(signal_data)
        self._save_history()
    
    def get_summary(self, symbol, interval):
        """
        Get signal summary with recommendation
        
        Args:
            symbol: Trading pair
            interval: Timeframe
        
        Returns:
            Signal summary with trading recommendation
        """
        signals = self.generate_signals(symbol, interval)
        
        if not signals['success']:
            return signals
        
        buy_count = signals['buy_signals']
        sell_count = signals['sell_signals']
        
        # Determine recommendation
        if buy_count > sell_count * 1.5:
            recommendation = 'STRONG BUY'
            confidence = min(95, 70 + (buy_count * 10))
        elif buy_count > sell_count:
            recommendation = 'BUY'
            confidence = min(90, 60 + (buy_count * 5))
        elif sell_count > buy_count * 1.5:
            recommendation = 'STRONG SELL'
            confidence = min(95, 70 + (sell_count * 10))
        elif sell_count > buy_count:
            recommendation = 'SELL'
            confidence = min(90, 60 + (sell_count * 5))
        else:
            recommendation = 'NEUTRAL'
            confidence = 50
        
        signals['recommendation'] = recommendation
        signals['recommendation_confidence'] = confidence
        
        return signals
    
    def get_history(self, limit=50):
        """Get signal history"""
        return self.signals_history[-limit:]

    def get_chart_data(self, symbol, interval, limit=100):
        """
        Get OHLCV candle data and signal markers formatted for TradingView
        Lightweight Charts.

        Args:
            symbol: Trading pair (e.g., 'ETHUSDT')
            interval: Timeframe (e.g., '15m')
            limit: Number of candles to return

        Returns:
            Dictionary with 'candles' (OHLCV list) and 'markers' (signal list)
        """
        df = self.binance.get_historical_data(symbol, interval, limit=limit)

        if df is None or len(df) == 0:
            return {'success': False, 'error': 'Failed to fetch data'}

        # Format candles for Lightweight Charts (time must be UTC unix seconds)
        candles = [
            {
                'time': int(row['open_time'].timestamp()),
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
            }
            for _, row in df.iterrows()
        ]

        # Detect all patterns across the full history
        detector = CandlestickPatterns(df)
        all_signals = detector.detect_all_patterns()

        # Build markers, keeping extra metadata for tooltip display
        markers = []
        for signal in all_signals:
            if signal['confidence'] < CONFIDENCE_THRESHOLD:
                continue
            idx = signal['index']
            if idx >= len(df):
                continue

            candle_time = int(df.iloc[idx]['open_time'].timestamp())
            sig_type = signal['signal']

            if sig_type == 'BUY':
                color = '#26a69a'
                position = 'belowBar'
                shape = 'arrowUp'
            elif sig_type == 'SELL':
                color = '#ef5350'
                position = 'aboveBar'
                shape = 'arrowDown'
            else:
                color = '#9e9e9e'
                position = 'inBar'
                shape = 'circle'

            markers.append({
                'time': candle_time,
                'position': position,
                'color': color,
                'shape': shape,
                'text': sig_type[0],  # 'B', 'S', or 'N'
                'size': 1,
                # Extra fields used by the frontend tooltip (ignored by chart lib)
                'pattern': signal['pattern'],
                'signal': sig_type,
                'confidence': signal['confidence'],
            })

        # Lightweight Charts requires markers sorted by time
        markers.sort(key=lambda m: m['time'])

        return {
            'success': True,
            'symbol': symbol,
            'interval': interval,
            'candles': candles,
            'markers': markers,
        }