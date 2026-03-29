# Crypto Candlestick Signal Bot

A real-time trading signal generator that detects candlestick patterns and generates buy/sell signals for cryptocurrency trading on Binance.

## Features

✅ **14+ Candlestick Patterns Detected**
- Engulfing (Bullish & Bearish)
- Hammer & Inverse Hammer
- Doji
- Morning Star & Evening Star
- Three White Soldiers & Three Black Crows
- Bullish & Bearish Harami
- Piercing Line & Dark Cloud Cover
- Shooting Star & Hanging Man

✅ **Real-time Signal Generation**
- Live candlestick analysis
- Confidence scoring for each pattern
- Aggregated buy/sell recommendations

✅ **Web Dashboard**
- Monitor signals in real-time
- Beautiful, responsive UI
- Auto-refresh capability
- Current price and candle data display

✅ **Flexible Configuration**
- Works with any trading pair (ETH/USDT, BTC/USDT, etc.)
- Configurable timeframes (1m, 5m, 15m, 1h, 4h, 1d, etc.)
- Adjustable confidence thresholds

✅ **Command-line Interface**
- Quick signal analysis
- History tracking
- Web server launcher

## Installation

### Prerequisites
- Python 3.7+
- Binance API key and secret
- Git

### Setup

1. **Clone the repository**
```bash
git clone https://github.com/dannzo55/crypto-candlestick-bot.git
cd crypto-candlestick-bot
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment variables**
```bash
cp .env.example .env
```

5. **Edit .env file with your credentials**
```
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_api_secret_here
TRADING_PAIR=ETHUSDT
TIMEFRAME=15m
FLASK_PORT=5000
```

## Usage

### Web Dashboard
```bash
python main.py --web
```
Then open your browser to `http://localhost:5000`

### Command Line
```bash
# Analyze current signals
python main.py

# Analyze specific pair and timeframe
python main.py --symbol BTCUSDT --interval 1h

# View signal history
python main.py --history 10
```

### Python API
```python
from signal_generator import SignalGenerator

gen = SignalGenerator()
signals = gen.get_summary('ETHUSDT', '15m')
print(f"Recommendation: {signals['recommendation']}")
print(f"Confidence: {signals['recommendation_confidence']}%")
```

## Configuration

Edit `config.py` to customize:

```python
# Which patterns to detect
PATTERNS_TO_DETECT = ['engulfing', 'hammer', 'doji', ...]

# Minimum confidence threshold (0-100)
CONFIDENCE_THRESHOLD = 70

# Signal history storage
MAX_HISTORY_RECORDS = 1000
```

## How It Works

1. **Data Fetching**: Fetches historical candlestick data from Binance API
2. **Pattern Detection**: Analyzes each candle against 14+ pattern definitions
3. **Signal Scoring**: Assigns confidence scores to detected patterns
4. **Recommendation**: Aggregates signals into BUY/SELL/NEUTRAL recommendations
5. **Display**: Shows results on web dashboard or CLI

## Supported Candlestick Patterns

| Pattern | Type | Signal | Confidence |
|---------|------|--------|-----------|
| Engulfing | Reversal | BUY/SELL | 85% |
| Hammer | Reversal | BUY | 75% |
| Inverse Hammer | Reversal | SELL | 75% |
| Doji | Indecision | NEUTRAL | 60% |
| Morning Star | Reversal | BUY | 80% |
| Evening Star | Reversal | SELL | 80% |
| Three White Soldiers | Continuation | BUY | 90% |
| Three Black Crows | Continuation | SELL | 90% |
| Bullish Harami | Reversal | BUY | 70% |
| Bearish Harami | Reversal | SELL | 70% |
| Piercing Line | Reversal | BUY | 75% |
| Dark Cloud Cover | Reversal | SELL | 75% |
| Shooting Star | Reversal | SELL | 75% |
| Hanging Man | Reversal | SELL | 75% |

## API Endpoints

### GET /api/signals
Get current signals for a pair
```
GET /api/signals?symbol=ETHUSDT&interval=15m
```

### GET /api/history
Get signal history
```
GET /api/history?limit=50
```

### POST /api/refresh
Force signal refresh
```
POST /api/refresh
Body: {"symbol": "ETHUSDT", "interval": "15m"}
```

### GET /health
Health check
```
GET /health
```

## Trading Pair Examples

- **Spot Trading**: ETHUSDT, BTCUSDT, BNBUSDT, ADAUSDT, etc.
- **Futures**: Not currently supported (can be added)

## Disclaimer

⚠️ **This bot is for educational and informational purposes only.**

- Trading cryptocurrencies carries significant risk
- Past patterns do not guarantee future results
- Always do your own research (DYOR)
- Start with small amounts
- Use proper risk management
- Crypto markets are highly volatile

## License

MIT License - See LICENSE file for details

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

If you encounter issues:
1. Check that your Binance API key is correct
2. Ensure you have the latest dependencies: `pip install -r requirements.txt --upgrade`
3. Check API rate limits on Binance
4. Review the logs for error messages

## Roadmap

- [ ] Multi-pair simultaneous monitoring
- [ ] Discord/Telegram notifications
- [ ] Database storage for signals
- [ ] Advanced indicators (RSI, MACD, etc.)
- [ ] Backtesting engine
- [ ] Live trading execution (paper trading first)
- [ ] Mobile app

## Contact

Created with 💚 for crypto traders

---

**Remember: This is a signal generator, not a guarantee. Always trade responsibly!**