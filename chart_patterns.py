import numpy as np
import pandas as pd


class ChartPatterns:
    """Detects chart patterns (head & shoulders, triangles, flags, etc.) in OHLC data"""

    def __init__(self, df):
        """Initialize with OHLC dataframe.
        df must have columns: open, high, low, close"""
        self.df = df.copy()
        self.closes = self.df['close'].values.astype(float)
        self.highs = self.df['high'].values.astype(float)
        self.lows = self.df['low'].values.astype(float)
        self.n = len(self.df)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _find_peaks(self, data, order=5):
        """Return indices of local maxima with the given neighbourhood order."""
        peaks = []
        for i in range(order, len(data) - order):
            window = data[i - order: i + order + 1]
            if data[i] == window.max():
                peaks.append(i)
        return peaks

    def _find_valleys(self, data, order=5):
        """Return indices of local minima with the given neighbourhood order."""
        valleys = []
        for i in range(order, len(data) - order):
            window = data[i - order: i + order + 1]
            if data[i] == window.min():
                valleys.append(i)
        return valleys

    @staticmethod
    def _within_pct(a, b, pct):
        """Return True if a and b are within *pct* percent of each other."""
        denom = max(abs(a), abs(b))
        if denom == 0:
            return True
        return abs(a - b) / denom <= pct

    # ------------------------------------------------------------------
    # 1. Head and Shoulders (Bearish reversal)
    # ------------------------------------------------------------------

    def head_and_shoulders(self):
        """Three peaks: left shoulder, higher head, right shoulder.
        Right shoulder ≈ left shoulder.  Bearish reversal signal."""
        signals = []
        peaks = self._find_peaks(self.highs)
        if len(peaks) < 3:
            return signals

        for i in range(len(peaks) - 2):
            ls, head, rs = peaks[i], peaks[i + 1], peaks[i + 2]
            ls_val = self.highs[ls]
            head_val = self.highs[head]
            rs_val = self.highs[rs]

            if (head_val > ls_val and
                    head_val > rs_val and
                    self._within_pct(ls_val, rs_val, 0.05)):
                signals.append({
                    'index': rs,
                    'pattern': 'head_and_shoulders',
                    'signal': 'SELL',
                    'confidence': 82
                })

        return signals

    # ------------------------------------------------------------------
    # 2. Inverse Head and Shoulders (Bullish reversal)
    # ------------------------------------------------------------------

    def inverse_head_and_shoulders(self):
        """Three valleys: left shoulder, lower head, right shoulder.
        Right shoulder ≈ left shoulder.  Bullish reversal signal."""
        signals = []
        valleys = self._find_valleys(self.lows)
        if len(valleys) < 3:
            return signals

        for i in range(len(valleys) - 2):
            ls, head, rs = valleys[i], valleys[i + 1], valleys[i + 2]
            ls_val = self.lows[ls]
            head_val = self.lows[head]
            rs_val = self.lows[rs]

            if (head_val < ls_val and
                    head_val < rs_val and
                    self._within_pct(ls_val, rs_val, 0.05)):
                signals.append({
                    'index': rs,
                    'pattern': 'inverse_head_and_shoulders',
                    'signal': 'BUY',
                    'confidence': 82
                })

        return signals

    # ------------------------------------------------------------------
    # 3. Double Top (Bearish reversal)
    # ------------------------------------------------------------------

    def double_top(self):
        """Two peaks at roughly the same price level. Bearish reversal."""
        signals = []
        peaks = self._find_peaks(self.highs)
        if len(peaks) < 2:
            return signals

        for i in range(len(peaks) - 1):
            p1, p2 = peaks[i], peaks[i + 1]
            if self._within_pct(self.highs[p1], self.highs[p2], 0.03):
                signals.append({
                    'index': p2,
                    'pattern': 'double_top',
                    'signal': 'SELL',
                    'confidence': 78
                })

        return signals

    # ------------------------------------------------------------------
    # 4. Double Bottom (Bullish reversal)
    # ------------------------------------------------------------------

    def double_bottom(self):
        """Two valleys at roughly the same price level. Bullish reversal."""
        signals = []
        valleys = self._find_valleys(self.lows)
        if len(valleys) < 2:
            return signals

        for i in range(len(valleys) - 1):
            v1, v2 = valleys[i], valleys[i + 1]
            if self._within_pct(self.lows[v1], self.lows[v2], 0.03):
                signals.append({
                    'index': v2,
                    'pattern': 'double_bottom',
                    'signal': 'BUY',
                    'confidence': 78
                })

        return signals

    # ------------------------------------------------------------------
    # 5. Ascending Triangle (Bullish continuation)
    # ------------------------------------------------------------------

    def ascending_triangle(self, window=20):
        """Flat resistance with rising lows over a rolling window.
        Bullish continuation pattern."""
        signals = []
        if self.n < window + 5:
            return signals

        for i in range(window, self.n):
            segment_highs = self.highs[i - window: i]
            segment_lows = self.lows[i - window: i]

            high_range = segment_highs.max() - segment_highs.min()
            if high_range / segment_highs.mean() > 0.02:
                continue

            x = np.arange(window)
            slope = np.polyfit(x, segment_lows, 1)[0]
            if slope > 0:
                signals.append({
                    'index': i,
                    'pattern': 'ascending_triangle',
                    'signal': 'BUY',
                    'confidence': 75
                })

        return signals

    # ------------------------------------------------------------------
    # 6. Descending Triangle (Bearish continuation)
    # ------------------------------------------------------------------

    def descending_triangle(self, window=20):
        """Flat support with falling highs over a rolling window.
        Bearish continuation pattern."""
        signals = []
        if self.n < window + 5:
            return signals

        for i in range(window, self.n):
            segment_highs = self.highs[i - window: i]
            segment_lows = self.lows[i - window: i]

            low_range = segment_lows.max() - segment_lows.min()
            if low_range / segment_lows.mean() > 0.02:
                continue

            x = np.arange(window)
            slope = np.polyfit(x, segment_highs, 1)[0]
            if slope < 0:
                signals.append({
                    'index': i,
                    'pattern': 'descending_triangle',
                    'signal': 'SELL',
                    'confidence': 75
                })

        return signals

    # ------------------------------------------------------------------
    # 7. Bullish Flag (Continuation)
    # ------------------------------------------------------------------

    def bullish_flag(self, pole_window=10, flag_window=10):
        """Sharp upward move (flagpole) followed by a slight downward channel.
        Bullish continuation pattern."""
        signals = []
        min_len = pole_window + flag_window
        if self.n < min_len + 2:
            return signals

        for i in range(min_len, self.n):
            pole = self.closes[i - min_len: i - flag_window]
            flag = self.closes[i - flag_window: i]

            if pole[0] == 0:
                continue
            pole_gain = (pole[-1] - pole[0]) / pole[0]
            if pole_gain < 0.04:
                continue

            x = np.arange(flag_window)
            flag_slope = np.polyfit(x, flag, 1)[0]
            if flag_slope < 0:
                signals.append({
                    'index': i,
                    'pattern': 'bullish_flag',
                    'signal': 'BUY',
                    'confidence': 76
                })

        return signals

    # ------------------------------------------------------------------
    # 8. Bearish Flag (Continuation)
    # ------------------------------------------------------------------

    def bearish_flag(self, pole_window=10, flag_window=10):
        """Sharp downward move (flagpole) followed by a slight upward channel.
        Bearish continuation pattern."""
        signals = []
        min_len = pole_window + flag_window
        if self.n < min_len + 2:
            return signals

        for i in range(min_len, self.n):
            pole = self.closes[i - min_len: i - flag_window]
            flag = self.closes[i - flag_window: i]

            if pole[0] == 0:
                continue
            pole_drop = (pole[0] - pole[-1]) / pole[0]
            if pole_drop < 0.04:
                continue

            x = np.arange(flag_window)
            flag_slope = np.polyfit(x, flag, 1)[0]
            if flag_slope > 0:
                signals.append({
                    'index': i,
                    'pattern': 'bearish_flag',
                    'signal': 'SELL',
                    'confidence': 76
                })

        return signals

    # ------------------------------------------------------------------
    # 9. Triple Top (Strong bearish reversal)
    # ------------------------------------------------------------------

    def triple_top(self):
        """Three peaks at approximately the same level. Strong bearish reversal."""
        signals = []
        peaks = self._find_peaks(self.highs)
        if len(peaks) < 3:
            return signals

        for i in range(len(peaks) - 2):
            p1, p2, p3 = peaks[i], peaks[i + 1], peaks[i + 2]
            v1, v2, v3 = self.highs[p1], self.highs[p2], self.highs[p3]

            if (self._within_pct(v1, v2, 0.03) and
                    self._within_pct(v2, v3, 0.03)):
                signals.append({
                    'index': p3,
                    'pattern': 'triple_top',
                    'signal': 'SELL',
                    'confidence': 85
                })

        return signals

    # ------------------------------------------------------------------
    # 10. Triple Bottom (Strong bullish reversal)
    # ------------------------------------------------------------------

    def triple_bottom(self):
        """Three valleys at approximately the same level. Strong bullish reversal."""
        signals = []
        valleys = self._find_valleys(self.lows)
        if len(valleys) < 3:
            return signals

        for i in range(len(valleys) - 2):
            v1, v2, v3 = valleys[i], valleys[i + 1], valleys[i + 2]
            lv1, lv2, lv3 = self.lows[v1], self.lows[v2], self.lows[v3]

            if (self._within_pct(lv1, lv2, 0.03) and
                    self._within_pct(lv2, lv3, 0.03)):
                signals.append({
                    'index': v3,
                    'pattern': 'triple_bottom',
                    'signal': 'BUY',
                    'confidence': 85
                })

        return signals

    # ------------------------------------------------------------------
    # Unified detection
    # ------------------------------------------------------------------

    def detect_all_patterns(self):
        """Detect all 10 chart patterns and return consolidated signals."""
        all_signals = []

        all_signals.extend(self.head_and_shoulders())
        all_signals.extend(self.inverse_head_and_shoulders())
        all_signals.extend(self.double_top())
        all_signals.extend(self.double_bottom())
        all_signals.extend(self.ascending_triangle())
        all_signals.extend(self.descending_triangle())
        all_signals.extend(self.bullish_flag())
        all_signals.extend(self.bearish_flag())
        all_signals.extend(self.triple_top())
        all_signals.extend(self.triple_bottom())

        return sorted(all_signals, key=lambda x: x['index'])