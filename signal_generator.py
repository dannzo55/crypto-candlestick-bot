from datetime import datetime
import json
from pathlib import Path
from patterns import CandlestickPatterns
from chart_patterns import ChartPatterns
from advanced_patterns import AdvancedPatterns
from binance_client import BinanceClient
from config import SIGNALS_HISTORY_FILE, MAX_HISTORY_RECORDS, CONFIDENCE_THRESHOLD, USE_ADVANCED_PATTERNS

class SignalGenerator:
    """Generates trading signals based on candlestick and chart patterns"""
    
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
        
        # Detect candlestick patterns
        detector = CandlestickPatterns(df)
        candlestick_signals = detector.detect_all_patterns()

        # Detect chart patterns
        chart_detector = ChartPatterns(df)
        chart_signals = chart_detector.detect_all_patterns()

        all_signals = candlestick_signals + chart_signals

        # Detect advanced patterns (if enabled)
        if USE_ADVANCED_PATTERNS and 'volume' in df.columns:
            advanced_detector = AdvancedPatterns(df)
            advanced_signals = advanced_detector.detect_all_patterns()
            all_signals = all_signals + advanced_signals

        # Apply pattern convergence boost: multiple patterns at the same candle
        # increase confidence to reward signal confirmation
        all_signals = self._apply_convergence_boost(all_signals)

        # Filter by confidence threshold
        filtered_signals = [
            s for s in all_signals
            if s['confidence'] >= CONFIDENCE_THRESHOLD
        ]
        
        # Add candle timestamps so the chart can place markers on the right candle
        for signal in filtered_signals:
            idx = signal.get('index', -1)
            if 0 <= idx < len(df):
                try:
                    signal['time'] = int(df.iloc[idx]['open_time'].timestamp())
                except (AttributeError, TypeError, OSError):
                    pass
        
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
    
    def _apply_convergence_boost(self, signals):
        """Boost confidence when multiple patterns converge at the same candle index.
        2 patterns: +10, 3 patterns: +20, 4+ patterns: +30 (capped at 95)."""
        from collections import defaultdict
        index_counts = defaultdict(int)
        for s in signals:
            index_counts[s['index']] += 1

        boosted = []
        for s in signals:
            count = index_counts[s['index']]
            boost = 0
            if count == 2:
                boost = 10
            elif count == 3:
                boost = 20
            elif count >= 4:
                boost = 30
            entry = dict(s)
            entry['confidence'] = min(95, entry['confidence'] + boost)
            if count > 1:
                entry['convergence_count'] = count
            boosted.append(entry)
        return boosted

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