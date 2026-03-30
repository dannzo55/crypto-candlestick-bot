import numpy as np
import pandas as pd


class AdvancedPatterns:
    """Detects 17 advanced day trading patterns in OHLC + volume data."""

    def __init__(self, df):
        """Initialize with OHLC + volume dataframe.
        df must have columns: open, high, low, close, volume"""
        self.df = df.copy()
        self.closes = self.df['close'].values.astype(float)
        self.opens = self.df['open'].values.astype(float)
        self.highs = self.df['high'].values.astype(float)
        self.lows = self.df['low'].values.astype(float)
        self.volumes = self.df['volume'].values.astype(float)
        self.n = len(self.df)
        # Cached values
        self._vwap = None
        self._support_resistance = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _find_peaks(self, data, order=5):
        """Return indices of local maxima within the given neighbourhood."""
        peaks = []
        for i in range(order, len(data) - order):
            window = data[i - order: i + order + 1]
            if data[i] == window.max():
                peaks.append(i)
        return peaks

    def _find_valleys(self, data, order=5):
        """Return indices of local minima within the given neighbourhood."""
        valleys = []
        for i in range(order, len(data) - order):
            window = data[i - order: i + order + 1]
            if data[i] == window.min():
                valleys.append(i)
        return valleys

    def _calculate_vwap(self):
        """Calculate and cache VWAP (Volume Weighted Average Price)."""
        if self._vwap is not None:
            return self._vwap
        typical_price = (self.highs + self.lows + self.closes) / 3
        cumulative_tp_vol = np.cumsum(typical_price * self.volumes)
        cumulative_vol = np.cumsum(self.volumes)
        with np.errstate(divide='ignore', invalid='ignore'):
            self._vwap = np.where(
                cumulative_vol > 0,
                cumulative_tp_vol / cumulative_vol,
                typical_price
            )
        return self._vwap

    def _find_support_resistance(self, window=20, num_levels=5):
        """Identify key support and resistance price levels using pivot points.
        Returns a tuple (support_levels, resistance_levels) as sorted lists."""
        if self._support_resistance is not None:
            return self._support_resistance
        pivots_high = []
        pivots_low = []
        order = 3
        for i in range(order, self.n - order):
            if self.highs[i] == max(self.highs[i - order: i + order + 1]):
                pivots_high.append(self.highs[i])
            if self.lows[i] == min(self.lows[i - order: i + order + 1]):
                pivots_low.append(self.lows[i])
        # Cluster nearby levels
        def cluster_levels(levels, tolerance=0.005):
            if not levels:
                return []
            levels = sorted(levels)
            clusters = [[levels[0]]]
            for level in levels[1:]:
                if abs(level - clusters[-1][-1]) / max(abs(clusters[-1][-1]), 1e-9) <= tolerance:
                    clusters[-1].append(level)
                else:
                    clusters.append([level])
            return [np.mean(c) for c in clusters]

        resistance = sorted(cluster_levels(pivots_high), reverse=True)[:num_levels]
        support = sorted(cluster_levels(pivots_low))[:num_levels]
        self._support_resistance = (support, resistance)
        return self._support_resistance

    def _detect_gaps(self):
        """Detect price gaps and return list of (index, gap_type, direction).
        gap_type: 'common', 'breakaway', 'runaway', or 'exhaustion'
        direction: 'up' or 'down'
        """
        gaps = []
        if self.n < 20:
            return gaps
        avg_vol = np.mean(self.volumes)
        for i in range(1, self.n):
            prev_close = self.closes[i - 1]
            curr_open = self.opens[i]
            gap_pct = (curr_open - prev_close) / max(abs(prev_close), 1e-9)
            if abs(gap_pct) < 0.003:
                continue
            direction = 'up' if gap_pct > 0 else 'down'
            # Classify the gap based on context
            lookback = min(i, 20)
            recent_closes = self.closes[i - lookback: i]
            recent_vol = np.mean(self.volumes[max(0, i - 5): i])
            price_range = recent_closes.max() - recent_closes.min()
            avg_close = recent_closes.mean()
            volatility = price_range / max(avg_close, 1e-9)
            # Trend before gap
            if lookback >= 5:
                trend_slope = np.polyfit(np.arange(lookback), recent_closes, 1)[0]
                trend_strength = abs(trend_slope) / max(avg_close, 1e-9)
            else:
                trend_strength = 0.0

            vol_spike = recent_vol > avg_vol * 1.5
            high_volatility = volatility > 0.03

            # Exhaustion: gap after extended trend with high volume
            if trend_strength > 0.001 and vol_spike and i > self.n * 0.7:
                gap_type = 'exhaustion'
            # Breakaway: gap at start of potential new trend with volume spike
            elif vol_spike and not high_volatility:
                gap_type = 'breakaway'
            # Runaway: gap in middle of trend
            elif trend_strength > 0.0005 and not vol_spike:
                gap_type = 'runaway'
            else:
                gap_type = 'common'
            gaps.append((i, gap_type, direction))
        return gaps

    def _volume_confirmation(self, idx, lookback=10, threshold=1.5):
        """Return True if volume at idx is significantly above recent average."""
        if idx < lookback:
            lookback = idx
        if lookback == 0:
            return False
        avg_vol = np.mean(self.volumes[idx - lookback: idx])
        return avg_vol > 0 and self.volumes[idx] > avg_vol * threshold

    def _is_rounding_pattern(self, prices, inverted=False):
        """Fit a polynomial to prices and check if it forms a U (or inverted-U) shape.
        Returns True if the shape matches."""
        if len(prices) < 5:
            return False
        x = np.arange(len(prices))
        try:
            coeffs = np.polyfit(x, prices, 2)
        except np.linalg.LinAlgError:
            return False
        a = coeffs[0]
        # Normalize by price scale to get relative curvature
        price_scale = max(abs(np.mean(prices)), 1e-9)
        relative_a = a / price_scale
        # Minimum curvature threshold
        threshold = 1e-6
        if inverted:
            return relative_a < -threshold
        return relative_a > threshold

    # ------------------------------------------------------------------
    # 1. Cup and Handle (Bullish Continuation)
    # ------------------------------------------------------------------

    def cup_and_handle(self, cup_window=30, handle_window=10):
        """Rounded bottom (cup) followed by a slight pullback (handle).
        Bullish continuation pattern."""
        signals = []
        min_len = cup_window + handle_window
        if self.n < min_len + 5:
            return signals

        for i in range(min_len, self.n):
            cup_prices = self.closes[i - min_len: i - handle_window]
            handle_prices = self.closes[i - handle_window: i]

            if not self._is_rounding_pattern(cup_prices, inverted=False):
                continue

            # Handle: slight downward slope, shallower than cup depth
            cup_depth = cup_prices.max() - cup_prices.min()
            handle_drop = handle_prices[0] - handle_prices[-1]
            if cup_depth == 0:
                continue
            if not (0 < handle_drop < cup_depth * 0.5):
                continue

            # Breakout: current close near cup rim
            cup_rim = cup_prices.max()
            if self.closes[i - 1] >= cup_rim * 0.98:
                signals.append({
                    'index': i - 1,
                    'pattern': 'cup_and_handle',
                    'signal': 'BUY',
                    'confidence': 80
                })

        return signals

    # ------------------------------------------------------------------
    # 2. Pennants (Continuation)
    # ------------------------------------------------------------------

    def pennants(self, pole_window=10, pennant_window=10):
        """Small symmetrical triangle after a sharp move.
        BUY after uptrend, SELL after downtrend."""
        signals = []
        min_len = pole_window + pennant_window
        if self.n < min_len + 2:
            return signals

        for i in range(min_len, self.n):
            pole = self.closes[i - min_len: i - pennant_window]
            pennant = self.closes[i - pennant_window: i]
            pennant_highs = self.highs[i - pennant_window: i]
            pennant_lows = self.lows[i - pennant_window: i]

            if pole[0] == 0:
                continue
            pole_move = (pole[-1] - pole[0]) / pole[0]
            if abs(pole_move) < 0.03:
                continue

            # Pennant: converging highs and lows.
            # Accept two cases: (1) highs falling AND lows rising (classic symmetrical),
            # or (2) both falling but highs fall faster than lows (downward-tilted pennant).
            x = np.arange(pennant_window)
            high_slope = np.polyfit(x, pennant_highs, 1)[0]
            low_slope = np.polyfit(x, pennant_lows, 1)[0]
            converging_symmetrical = high_slope < 0 < low_slope
            converging_downward = high_slope < 0 and low_slope < 0 and high_slope < low_slope
            if not (converging_symmetrical or converging_downward):
                continue

            signal = 'BUY' if pole_move > 0 else 'SELL'
            signals.append({
                'index': i - 1,
                'pattern': 'pennant',
                'signal': signal,
                'confidence': 75
            })

        return signals

    # ------------------------------------------------------------------
    # 3. Symmetrical Triangle (Consolidation/Breakout)
    # ------------------------------------------------------------------

    def symmetrical_triangle(self, window=20):
        """Converging highs and lows. Direction depends on breakout."""
        signals = []
        if self.n < window + 5:
            return signals

        for i in range(window, self.n):
            seg_highs = self.highs[i - window: i]
            seg_lows = self.lows[i - window: i]
            x = np.arange(window)
            high_slope = np.polyfit(x, seg_highs, 1)[0]
            low_slope = np.polyfit(x, seg_lows, 1)[0]

            # Both must converge (highs falling, lows rising)
            if not (high_slope < 0 and low_slope > 0):
                continue

            # Breakout detection: current close vs triangle boundary
            projected_high = seg_highs[-1] + high_slope
            projected_low = seg_lows[-1] + low_slope
            curr_close = self.closes[i - 1]

            if curr_close > projected_high * 0.99:
                signals.append({
                    'index': i - 1,
                    'pattern': 'symmetrical_triangle',
                    'signal': 'BUY',
                    'confidence': 72
                })
            elif curr_close < projected_low * 1.01:
                signals.append({
                    'index': i - 1,
                    'pattern': 'symmetrical_triangle',
                    'signal': 'SELL',
                    'confidence': 72
                })

        return signals

    # ------------------------------------------------------------------
    # 4. Rising Wedge (Bearish Reversal)
    # ------------------------------------------------------------------

    def rising_wedge(self, window=20):
        """Rising lows and highs, but highs rise faster. Bearish reversal."""
        signals = []
        if self.n < window + 5:
            return signals

        for i in range(window, self.n):
            seg_highs = self.highs[i - window: i]
            seg_lows = self.lows[i - window: i]
            x = np.arange(window)
            high_slope = np.polyfit(x, seg_highs, 1)[0]
            low_slope = np.polyfit(x, seg_lows, 1)[0]

            if high_slope > 0 and low_slope > 0 and high_slope > low_slope:
                signals.append({
                    'index': i - 1,
                    'pattern': 'rising_wedge',
                    'signal': 'SELL',
                    'confidence': 78
                })

        return signals

    # ------------------------------------------------------------------
    # 5. Falling Wedge (Bullish Reversal)
    # ------------------------------------------------------------------

    def falling_wedge(self, window=20):
        """Falling lows and highs, but lows fall faster. Bullish reversal."""
        signals = []
        if self.n < window + 5:
            return signals

        for i in range(window, self.n):
            seg_highs = self.highs[i - window: i]
            seg_lows = self.lows[i - window: i]
            x = np.arange(window)
            high_slope = np.polyfit(x, seg_highs, 1)[0]
            low_slope = np.polyfit(x, seg_lows, 1)[0]

            if high_slope < 0 and low_slope < 0 and low_slope < high_slope:
                signals.append({
                    'index': i - 1,
                    'pattern': 'falling_wedge',
                    'signal': 'BUY',
                    'confidence': 78
                })

        return signals

    # ------------------------------------------------------------------
    # 6. Breakout Patterns (Momentum)
    # ------------------------------------------------------------------

    def breakout_patterns(self, window=20):
        """Price breaks above resistance or below support with volume confirmation."""
        signals = []
        if self.n < window + 5:
            return signals

        for i in range(window, self.n):
            seg_highs = self.highs[i - window: i - 1]
            seg_lows = self.lows[i - window: i - 1]
            resistance = seg_highs.max()
            support = seg_lows.min()
            curr_close = self.closes[i - 1]

            if curr_close > resistance and self._volume_confirmation(i - 1):
                signals.append({
                    'index': i - 1,
                    'pattern': 'breakout',
                    'signal': 'BUY',
                    'confidence': 75
                })
            elif curr_close < support and self._volume_confirmation(i - 1):
                signals.append({
                    'index': i - 1,
                    'pattern': 'breakout',
                    'signal': 'SELL',
                    'confidence': 75
                })

        return signals

    # ------------------------------------------------------------------
    # 7-10. Gap Patterns (4 types)
    # ------------------------------------------------------------------

    def gap_patterns(self):
        """Detect and classify gaps: common, breakaway, runaway, exhaustion."""
        signals = []
        gaps = self._detect_gaps()

        confidence_map = {
            'common': 60,
            'breakaway': 80,
            'runaway': 75,
            'exhaustion': 70
        }

        for idx, gap_type, direction in gaps:
            if gap_type == 'common':
                sig = 'NEUTRAL'
            elif gap_type == 'exhaustion':
                # Reversal signal: opposite of gap direction
                sig = 'SELL' if direction == 'up' else 'BUY'
            else:
                sig = 'BUY' if direction == 'up' else 'SELL'

            signals.append({
                'index': idx,
                'pattern': f'gap_{gap_type}',
                'signal': sig,
                'confidence': confidence_map[gap_type]
            })

        return signals

    # ------------------------------------------------------------------
    # 11. Island Reversal
    # ------------------------------------------------------------------

    def island_reversal(self, gap_threshold=0.003):
        """Price gaps on both sides, creating an isolated island.
        BUY (bullish reversal) or SELL (bearish reversal)."""
        signals = []
        if self.n < 5:
            return signals

        for i in range(2, self.n - 1):
            # Gap up before island, gap down after (bearish island top)
            gap_before_up = (self.opens[i] - self.closes[i - 1]) / max(abs(self.closes[i - 1]), 1e-9)
            gap_after_down = (self.opens[i + 1] - self.closes[i]) / max(abs(self.closes[i]), 1e-9)
            if gap_before_up > gap_threshold and gap_after_down < -gap_threshold:
                signals.append({
                    'index': i,
                    'pattern': 'island_reversal',
                    'signal': 'SELL',
                    'confidence': 82
                })
                continue

            # Gap down before island, gap up after (bullish island bottom)
            gap_before_down = (self.opens[i] - self.closes[i - 1]) / max(abs(self.closes[i - 1]), 1e-9)
            gap_after_up = (self.opens[i + 1] - self.closes[i]) / max(abs(self.closes[i]), 1e-9)
            if gap_before_down < -gap_threshold and gap_after_up > gap_threshold:
                signals.append({
                    'index': i,
                    'pattern': 'island_reversal',
                    'signal': 'BUY',
                    'confidence': 82
                })

        return signals

    # ------------------------------------------------------------------
    # 12. Volume Spike with Price Action
    # ------------------------------------------------------------------

    def volume_spike(self, lookback=20, vol_multiplier=2.0, price_threshold=0.01):
        """Sharp price move with significant volume increase."""
        signals = []
        if self.n < lookback + 2:
            return signals

        for i in range(lookback, self.n):
            avg_vol = np.mean(self.volumes[i - lookback: i])
            if avg_vol == 0:
                continue
            if self.volumes[i] < avg_vol * vol_multiplier:
                continue

            price_change = (self.closes[i] - self.opens[i]) / max(abs(self.opens[i]), 1e-9)
            if price_change > price_threshold:
                signals.append({
                    'index': i,
                    'pattern': 'volume_spike',
                    'signal': 'BUY',
                    'confidence': 76
                })
            elif price_change < -price_threshold:
                signals.append({
                    'index': i,
                    'pattern': 'volume_spike',
                    'signal': 'SELL',
                    'confidence': 76
                })

        return signals

    # ------------------------------------------------------------------
    # 13. Support Bounces
    # ------------------------------------------------------------------

    def support_bounces(self, tolerance=0.01):
        """Price bounces off support level with increased volume. BUY signal."""
        signals = []
        if self.n < 30:
            return signals

        support_levels, _ = self._find_support_resistance()
        if not support_levels:
            return signals

        for i in range(1, self.n):
            curr_low = self.lows[i]
            for level in support_levels:
                if abs(curr_low - level) / max(abs(level), 1e-9) <= tolerance:
                    if self.closes[i] > self.opens[i] and self._volume_confirmation(i):
                        signals.append({
                            'index': i,
                            'pattern': 'support_bounce',
                            'signal': 'BUY',
                            'confidence': 74
                        })
                        break

        return signals

    # ------------------------------------------------------------------
    # 14. Resistance Bounces
    # ------------------------------------------------------------------

    def resistance_bounces(self, tolerance=0.01):
        """Price bounces off resistance level with increased volume. SELL signal."""
        signals = []
        if self.n < 30:
            return signals

        _, resistance_levels = self._find_support_resistance()
        if not resistance_levels:
            return signals

        for i in range(1, self.n):
            curr_high = self.highs[i]
            for level in resistance_levels:
                if abs(curr_high - level) / max(abs(level), 1e-9) <= tolerance:
                    if self.closes[i] < self.opens[i] and self._volume_confirmation(i):
                        signals.append({
                            'index': i,
                            'pattern': 'resistance_bounce',
                            'signal': 'SELL',
                            'confidence': 74
                        })
                        break

        return signals

    # ------------------------------------------------------------------
    # 15. VWAP Reversals
    # ------------------------------------------------------------------

    def vwap_reversals(self, tolerance=0.005):
        """Price reverses at VWAP level with volume confirmation."""
        signals = []
        if self.n < 10:
            return signals

        vwap = self._calculate_vwap()

        for i in range(1, self.n):
            distance = abs(self.closes[i] - vwap[i]) / max(abs(vwap[i]), 1e-9)
            if distance > tolerance:
                continue
            if not self._volume_confirmation(i):
                continue

            prev_close = self.closes[i - 1]
            curr_close = self.closes[i]
            if prev_close < vwap[i - 1] and curr_close > vwap[i]:
                signals.append({
                    'index': i,
                    'pattern': 'vwap_reversal',
                    'signal': 'BUY',
                    'confidence': 77
                })
            elif prev_close > vwap[i - 1] and curr_close < vwap[i]:
                signals.append({
                    'index': i,
                    'pattern': 'vwap_reversal',
                    'signal': 'SELL',
                    'confidence': 77
                })

        return signals

    # ------------------------------------------------------------------
    # 16. Rounding Bottom (Bullish Reversal)
    # ------------------------------------------------------------------

    def rounding_bottom(self, window=30):
        """Gradual U-shaped bottom, marks a trend reversal. BUY signal."""
        signals = []
        if self.n < window + 5:
            return signals

        for i in range(window, self.n):
            segment = self.closes[i - window: i]
            if self._is_rounding_pattern(segment, inverted=False):
                # Confirm: price is now above the midpoint of the cup
                mid = (segment.max() + segment.min()) / 2
                if self.closes[i - 1] > mid:
                    signals.append({
                        'index': i - 1,
                        'pattern': 'rounding_bottom',
                        'signal': 'BUY',
                        'confidence': 76
                    })

        return signals

    # ------------------------------------------------------------------
    # 17. Rounding Top (Bearish Reversal)
    # ------------------------------------------------------------------

    def rounding_top(self, window=30):
        """Gradual inverted U-shaped top, marks a trend reversal. SELL signal."""
        signals = []
        if self.n < window + 5:
            return signals

        for i in range(window, self.n):
            segment = self.closes[i - window: i]
            if self._is_rounding_pattern(segment, inverted=True):
                # Confirm: price is now below the midpoint of the dome
                mid = (segment.max() + segment.min()) / 2
                if self.closes[i - 1] < mid:
                    signals.append({
                        'index': i - 1,
                        'pattern': 'rounding_top',
                        'signal': 'SELL',
                        'confidence': 76
                    })

        return signals

    # ------------------------------------------------------------------
    # Unified detection
    # ------------------------------------------------------------------

    def detect_all_patterns(self):
        """Detect all 17 advanced patterns and return consolidated signals sorted by index."""
        all_signals = []

        all_signals.extend(self.cup_and_handle())
        all_signals.extend(self.pennants())
        all_signals.extend(self.symmetrical_triangle())
        all_signals.extend(self.rising_wedge())
        all_signals.extend(self.falling_wedge())
        all_signals.extend(self.breakout_patterns())
        all_signals.extend(self.gap_patterns())
        all_signals.extend(self.island_reversal())
        all_signals.extend(self.volume_spike())
        all_signals.extend(self.support_bounces())
        all_signals.extend(self.resistance_bounces())
        all_signals.extend(self.vwap_reversals())
        all_signals.extend(self.rounding_bottom())
        all_signals.extend(self.rounding_top())

        return sorted(all_signals, key=lambda x: x['index'])
