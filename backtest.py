import json
from datetime import datetime
import matplotlib.pyplot as plt
import mplfinance as mpf

# ----------------- CONFIG -----------------
HISTORY_FILE = 'signals_history.json'
START_BALANCE = 1000
RISK_PER_TRADE = 0.10  # 10%
# ------------------------------------------

# Load history
with open(HISTORY_FILE, 'r') as f:
    history = json.load(f)

# Prepare data lists
ohlc = []
buy_signals = []
sell_signals = []
equity_curve = []
balance = START_BALANCE

for entry in history:
    t = datetime.fromtimestamp(int(entry['timestamp']) / 1000)  # Convert string ms to datetime
    open_price = float(entry['last_candle']['open'])
    high_price = float(entry['last_candle']['high'])
    low_price = float(entry['last_candle']['low'])
    close_price = float(entry['last_candle']['close'])

    ohlc.append({
        'Date': t,
        'Open': open_price,
        'High': high_price,
        'Low': low_price,
        'Close': close_price
    })

    # Simulate trades
    rec = entry['recommendation'].upper()
    trade_size = balance * RISK_PER_TRADE

    if rec in ['BUY', 'STRONG BUY']:
        buy_signals.append((t, close_price))
        sell_signals.append(None)
        # Profit if price goes up during candle
        balance += (close_price - open_price) / open_price * trade_size
    elif rec in ['SELL', 'STRONG SELL']:
        sell_signals.append((t, close_price))
        buy_signals.append(None)
        # Profit if price goes down during candle
        balance += (open_price - close_price) / open_price * trade_size
    else:
        buy_signals.append(None)
        sell_signals.append(None)

    equity_curve.append(balance)

# Convert OHLC to DataFrame
import pandas as pd

df = pd.DataFrame(ohlc)
df.set_index('Date', inplace=True)

# Plot candlestick chart with signals
apds = [
    mpf.make_addplot([s[1] if s else None for s in buy_signals], type='scatter', markersize=100, marker='^',
                     color='green'),
    mpf.make_addplot([s[1] if s else None for s in sell_signals], type='scatter', markersize=100, marker='v',
                     color='red')
]

mpf.plot(
    df,
    type='candle',
    style='charles',
    title='Backtest Candlestick Signals',
    ylabel='Price ($)',
    addplot=apds,
    volume=False,
    figsize=(14, 8)
)

# Plot equity curve
plt.figure(figsize=(14, 5))
plt.plot(df.index, equity_curve, label='Equity Curve', color='blue', linewidth=2)
plt.title('Equity Curve')
plt.ylabel('Balance ($)')
plt.xlabel('Time')
plt.grid(True)
plt.legend()
plt.show()