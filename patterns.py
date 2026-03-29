import pandas as pd
import numpy as np

class CandlestickPatterns:
    """Detects various candlestick patterns in OHLC data"""
    
    def __init__(self, df):
        """Initialize with OHLC dataframe
        df should have columns: open, high, low, close"""
        self.df = df.copy()
        self._calculate_body_shadow()
    
    def _calculate_body_shadow(self):
        """Calculate candle body and shadow sizes"""
        self.df['body'] = abs(self.df['close'] - self.df['open'])
        self.df['upper_shadow'] = self.df['high'] - self.df[['open', 'close']].max(axis=1)
        self.df['lower_shadow'] = self.df[['open', 'close']].min(axis=1) - self.df['low']
        self.df['range'] = self.df['high'] - self.df['low']
        self.df['is_bullish'] = self.df['close'] > self.df['open']
    
    def engulfing(self, threshold=0.8):
        """Bullish Engulfing: Small bearish candle followed by large bullish candle
        Bearish Engulfing: Small bullish candle followed by large bearish candle"""
        signals = []
        
        for i in range(1, len(self.df)):
            prev = self.df.iloc[i-1]
            curr = self.df.iloc[i]
            
            # Bullish Engulfing
            if (not prev['is_bullish'] and curr['is_bullish'] and
                curr['open'] < prev['close'] and curr['close'] > prev['open']):
                signals.append({
                    'index': i,
                    'pattern': 'bullish_engulfing',
                    'signal': 'BUY',
                    'confidence': 85
                })
            
            # Bearish Engulfing
            if (prev['is_bullish'] and not curr['is_bullish'] and
                curr['open'] > prev['close'] and curr['close'] < prev['open']):
                signals.append({
                    'index': i,
                    'pattern': 'bearish_engulfing',
                    'signal': 'SELL',
                    'confidence': 85
                })
        
        return signals
    
    def hammer(self):
        """Hammer: Small body at top, long lower shadow
        Inverse Hammer: Small body at bottom, long upper shadow"""
        signals = []
        
        for i in range(len(self.df)):
            candle = self.df.iloc[i]
            
            if candle['range'] == 0:
                continue
            
            # Hammer (bullish reversal)
            if (candle['is_bullish'] and 
                candle['lower_shadow'] > 2 * candle['body'] and
                candle['upper_shadow'] < candle['body']):
                signals.append({
                    'index': i,
                    'pattern': 'hammer',
                    'signal': 'BUY',
                    'confidence': 75
                })
            
            # Inverse Hammer (bearish reversal)
            if (not candle['is_bullish'] and
                candle['upper_shadow'] > 2 * candle['body'] and
                candle['lower_shadow'] < candle['body']):
                signals.append({
                    'index': i,
                    'pattern': 'inverse_hammer',
                    'signal': 'SELL',
                    'confidence': 75
                })
        
        return signals
    
    def doji(self, threshold=0.1):
        """Doji: Open and close are very similar, long shadows
        Indicates indecision"""
        signals = []
        
        for i in range(len(self.df)):
            candle = self.df.iloc[i]
            
            if candle['range'] == 0:
                continue
            
            body_ratio = candle['body'] / candle['range']
            
            if body_ratio < threshold:
                signals.append({
                    'index': i,
                    'pattern': 'doji',
                    'signal': 'NEUTRAL',
                    'confidence': 60
                })
        
        return signals
    
    def morning_star(self):
        """Morning Star: Bearish candle, small body candle, bullish candle
        Bullish reversal pattern"""
        signals = []
        
        for i in range(2, len(self.df)):
            c1 = self.df.iloc[i-2]
            c2 = self.df.iloc[i-1]
            c3 = self.df.iloc[i]
            
            if (not c1['is_bullish'] and c3['is_bullish'] and
                c2['body'] < c1['body'] and c2['body'] < c3['body']):
                signals.append({
                    'index': i,
                    'pattern': 'morning_star',
                    'signal': 'BUY',
                    'confidence': 80
                })
        
        return signals
    
    def evening_star(self):
        """Evening Star: Bullish candle, small body candle, bearish candle
        Bearish reversal pattern"""
        signals = []
        
        for i in range(2, len(self.df)):
            c1 = self.df.iloc[i-2]
            c2 = self.df.iloc[i-1]
            c3 = self.df.iloc[i]
            
            if (c1['is_bullish'] and not c3['is_bullish'] and
                c2['body'] < c1['body'] and c2['body'] < c3['body']):
                signals.append({
                    'index': i,
                    'pattern': 'evening_star',
                    'signal': 'SELL',
                    'confidence': 80
                })
        
        return signals
    
    def three_white_soldiers(self):
        """Three White Soldiers: Three consecutive bullish candles with higher closes
        Strong bullish signal"""
        signals = []
        
        for i in range(2, len(self.df)):
            c1 = self.df.iloc[i-2]
            c2 = self.df.iloc[i-1]
            c3 = self.df.iloc[i]
            
            if (c1['is_bullish'] and c2['is_bullish'] and c3['is_bullish'] and
                c1['close'] < c2['close'] < c3['close']):
                signals.append({
                    'index': i,
                    'pattern': 'three_white_soldiers',
                    'signal': 'BUY',
                    'confidence': 90
                })
        
        return signals
    
    def three_black_crows(self):
        """Three Black Crows: Three consecutive bearish candles with lower closes
        Strong bearish signal"""
        signals = []
        
        for i in range(2, len(self.df)):
            c1 = self.df.iloc[i-2]
            c2 = self.df.iloc[i-1]
            c3 = self.df.iloc[i]
            
            if (not c1['is_bullish'] and not c2['is_bullish'] and not c3['is_bullish'] and
                c1['close'] > c2['close'] > c3['close']):
                signals.append({
                    'index': i,
                    'pattern': 'three_black_crows',
                    'signal': 'SELL',
                    'confidence': 90
                })
        
        return signals
    
    def bullish_harami(self):
        """Bullish Harami: Large bearish candle followed by small bullish candle inside it
        Potential reversal"""
        signals = []
        
        for i in range(1, len(self.df)):
            prev = self.df.iloc[i-1]
            curr = self.df.iloc[i]
            
            if (not prev['is_bullish'] and curr['is_bullish'] and
                curr['open'] > prev['close'] and curr['close'] < prev['open'] and
                curr['high'] < prev['high'] and curr['low'] > prev['low']):
                signals.append({
                    'index': i,
                    'pattern': 'bullish_harami',
                    'signal': 'BUY',
                    'confidence': 70
                })
        
        return signals
    
    def bearish_harami(self):
        """Bearish Harami: Large bullish candle followed by small bearish candle inside it
        Potential reversal"""
        signals = []
        
        for i in range(1, len(self.df)):
            prev = self.df.iloc[i-1]
            curr = self.df.iloc[i]
            
            if (prev['is_bullish'] and not curr['is_bullish'] and
                curr['open'] < prev['close'] and curr['close'] > prev['open'] and
                curr['high'] < prev['high'] and curr['low'] > prev['low']):
                signals.append({
                    'index': i,
                    'pattern': 'bearish_harami',
                    'signal': 'SELL',
                    'confidence': 70
                })
        
        return signals
    
    def piercing_line(self):
        """Piercing Line: Bearish candle followed by bullish candle closing above midpoint
        Bullish reversal"""
        signals = []
        
        for i in range(1, len(self.df)):
            prev = self.df.iloc[i-1]
            curr = self.df.iloc[i]
            
            midpoint = (prev['open'] + prev['close']) / 2
            
            if (not prev['is_bullish'] and curr['is_bullish'] and
                curr['open'] < prev['close'] and curr['close'] > midpoint):
                signals.append({
                    'index': i,
                    'pattern': 'piercing_line',
                    'signal': 'BUY',
                    'confidence': 75
                })
        
        return signals
    
    def dark_cloud_cover(self):
        """Dark Cloud Cover: Bullish candle followed by bearish candle closing below midpoint
        Bearish reversal"""
        signals = []
        
        for i in range(1, len(self.df)):
            prev = self.df.iloc[i-1]
            curr = self.df.iloc[i]
            
            midpoint = (prev['open'] + prev['close']) / 2
            
            if (prev['is_bullish'] and not curr['is_bullish'] and
                curr['open'] > prev['close'] and curr['close'] < midpoint):
                signals.append({
                    'index': i,
                    'pattern': 'dark_cloud_cover',
                    'signal': 'SELL',
                    'confidence': 75
                })
        
        return signals
    
    def shooting_star(self):
        """Shooting Star: Small body with long upper shadow, bearish reversal"""
        signals = []
        
        for i in range(len(self.df)):
            candle = self.df.iloc[i]
            
            if candle['range'] == 0:
                continue
            
            if (candle['is_bullish'] and
                candle['upper_shadow'] > 2 * candle['body'] and
                candle['lower_shadow'] < candle['body']):
                signals.append({
                    'index': i,
                    'pattern': 'shooting_star',
                    'signal': 'SELL',
                    'confidence': 75
                })
        
        return signals
    
    def hanging_man(self):
        """Hanging Man: Small body with long lower shadow, bearish reversal"""
        signals = []
        
        for i in range(len(self.df)):
            candle = self.df.iloc[i]
            
            if candle['range'] == 0:
                continue
            
            if (not candle['is_bullish'] and
                candle['lower_shadow'] > 2 * candle['body'] and
                candle['upper_shadow'] < candle['body']):
                signals.append({
                    'index': i,
                    'pattern': 'hanging_man',
                    'signal': 'SELL',
                    'confidence': 75
                })
        
        return signals
    
    def detect_all_patterns(self):
        """Detect all patterns and return consolidated signals"""
        all_signals = []
        
        all_signals.extend(self.engulfing())
        all_signals.extend(self.hammer())
        all_signals.extend(self.doji())
        all_signals.extend(self.morning_star())
        all_signals.extend(self.evening_star())
        all_signals.extend(self.three_white_soldiers())
        all_signals.extend(self.three_black_crows())
        all_signals.extend(self.bullish_harami())
        all_signals.extend(self.bearish_harami())
        all_signals.extend(self.piercing_line())
        all_signals.extend(self.dark_cloud_cover())
        all_signals.extend(self.shooting_star())
        all_signals.extend(self.hanging_man())
        
        return sorted(all_signals, key=lambda x: x['index'])