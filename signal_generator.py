from datetime import datetime
import json
import numpy as np
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
        
        # Determine market trend
        trend_info = self._get_trend_direction(df)

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
            'trend': {
                'direction': trend_info['direction'],
                'strength': round(trend_info['strength'], 2),
                'methods': {
                    'moving_average': trend_info['ma_trend'],
                    'higher_lows_highs': trend_info['hl_trend'],
                    'linear_regression': trend_info['slope_trend']
                }
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
    
    def _get_trend_direction(self, df):
        """
        Determine market trend using hybrid 3-method approach

        Methods:
        1. Moving Averages (40% weight) - Shows medium-term trend
        2. Higher Highs/Lows (40% weight) - Shows structure
        3. Linear Regression (20% weight) - Shows mathematical slope

        Returns:
            dict with direction, strength, and individual method results
        """
        if len(df) < 20:
            return {
                'direction': 'INSUFFICIENT_DATA',
                'strength': 0,
                'ma_trend': 'UNKNOWN',
                'hl_trend': 'UNKNOWN',
                'slope_trend': 'UNKNOWN'
            }

        close = df['close'].values
        high = df['high'].values
        low = df['low'].values

        # METHOD 1: Moving Average Analysis (40% weight)
        ma_9 = close[-9:].mean()
        ma_20 = close[-20:].mean()

        if close[-1] > ma_9 and ma_9 > ma_20:
            ma_trend = 'UPTREND'
        elif close[-1] < ma_9 and ma_9 < ma_20:
            ma_trend = 'DOWNTREND'
        else:
            ma_trend = 'SIDEWAYS'

        # METHOD 2: Higher Highs/Lows Detection (40% weight)
        if high[-1] > max(high[-5:-1]) and low[-1] > max(low[-5:-1]):
            hl_trend = 'UPTREND'
        elif high[-1] < min(high[-5:-1]) and low[-1] < min(low[-5:-1]):
            hl_trend = 'DOWNTREND'
        else:
            hl_trend = 'SIDEWAYS'

        # METHOD 3: Linear Regression Slope (20% weight)
        x = np.arange(20)
        y = close[-20:].astype(float)
        coefficients = np.polyfit(x, y, 1)
        slope = coefficients[0]

        close_mean = close[-20:].mean()
        slope_pct = (slope / close_mean * 100) if close_mean != 0 else 0

        if slope_pct > 0.05:
            slope_trend = 'UPTREND'
        elif slope_pct < -0.05:
            slope_trend = 'DOWNTREND'
        else:
            slope_trend = 'SIDEWAYS'

        # WEIGHTED VOTING (40 + 40 + 20 = 100)
        trend_votes = {
            'UPTREND': 0,
            'DOWNTREND': 0,
            'SIDEWAYS': 0
        }

        trend_votes[ma_trend] += 0.40
        trend_votes[hl_trend] += 0.40
        trend_votes[slope_trend] += 0.20

        direction = max(trend_votes, key=trend_votes.get)
        strength = max(trend_votes.values())

        return {
            'direction': direction,
            'strength': strength,
            'ma_trend': ma_trend,
            'hl_trend': hl_trend,
            'slope_trend': slope_trend
        }

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
        trend = signals['trend']['direction']
        trend_strength = signals['trend']['strength']
        
        # Determine recommendation with trend context
        if buy_count > sell_count * 1.5:
            recommendation = 'STRONG BUY'
            confidence = min(95, 70 + (buy_count * 10))

            if trend == 'UPTREND':
                confidence = min(98, confidence + int(5 * trend_strength))
                recommendation += ' (Trend-Aligned)'

        elif buy_count > sell_count:
            recommendation = 'BUY'
            confidence = min(90, 60 + (buy_count * 5))

            if trend == 'UPTREND':
                confidence = min(93, confidence + int(3 * trend_strength))

        elif sell_count > buy_count * 1.5:
            recommendation = 'STRONG SELL'
            confidence = min(95, 70 + (sell_count * 10))

            if trend == 'DOWNTREND':
                confidence = min(98, confidence + int(5 * trend_strength))
                recommendation += ' (Trend-Aligned)'

        elif sell_count > buy_count:
            recommendation = 'SELL'
            confidence = min(90, 60 + (sell_count * 5))

            if trend == 'DOWNTREND':
                confidence = min(93, confidence + int(3 * trend_strength))

        else:
            recommendation = 'NEUTRAL'
            confidence = 50
        
        signals['recommendation'] = recommendation
        signals['recommendation_confidence'] = confidence
        signals['trend_context'] = trend
        
        return signals
    
    def get_history(self, limit=50):
        """Get signal history"""
        return self.signals_history[-limit:]