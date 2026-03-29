import os
from dotenv import load_dotenv

load_dotenv()

# Binance API Configuration
BINANCE_API_KEY = os.getenv('BINANCE_API_KEY', '')
BINANCE_API_SECRET = os.getenv('BINANCE_API_SECRET', '')

# Trading Configuration
TRADING_PAIR = os.getenv('TRADING_PAIR', 'ETHUSDT')
TIMEFRAME = os.getenv('TIMEFRAME', '15m')

# Supported timeframes
SUPPORTED_TIMEFRAMES = ['1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w', '1M']

# Flask Configuration
FLASK_PORT = int(os.getenv('FLASK_PORT', 5000))
FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'

# Pattern Detection Settings
PATTERNS_TO_DETECT = [
    'engulfing',
    'hammer',
    'inverse_hammer',
    'doji',
    'morning_star',
    'evening_star',
    'three_white_soldiers',
    'three_black_crows',
    'bullish_harami',
    'bearish_harami',
    'piercing_line',
    'dark_cloud_cover',
    'shooting_star',
    'hanging_man',
]

# Signal Confidence Threshold (0-100)
CONFIDENCE_THRESHOLD = 70

# Data Storage
SIGNALS_HISTORY_FILE = 'signals_history.json'
MAX_HISTORY_RECORDS = 1000
