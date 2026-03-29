from flask import Flask, render_template, jsonify, request
from signal_generator import SignalGenerator
from config import FLASK_PORT, FLASK_DEBUG, TRADING_PAIR, TIMEFRAME
import json

app = Flask(__name__)
signal_gen = SignalGenerator()


@app.route('/')
def index():
    """Main dashboard"""
    return render_template('index.html')


@app.route('/api/signals', methods=['GET'])
def get_signals():
    """Get current signals"""
    symbol = request.args.get('symbol', TRADING_PAIR)
    interval = request.args.get('interval', TIMEFRAME)

    signals = signal_gen.get_summary(symbol, interval)
    return jsonify({
        "success": True,
        **signals
    })


@app.route('/api/candles', methods=['GET'])
def get_candles():
    """Get OHLCV candlestick data for chart rendering"""
    symbol = request.args.get('symbol', TRADING_PAIR)
    interval = request.args.get('interval', TIMEFRAME)
    limit = request.args.get('limit', 100, type=int)

    df = signal_gen.binance.get_historical_data(symbol, interval, limit=limit)

    if df is None:
        return jsonify({'success': False, 'error': 'Failed to fetch candle data'})

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
    return jsonify({'success': True, 'candles': candles})


@app.route('/api/history', methods=['GET'])
def get_history():
    """Get signal history"""
    limit = request.args.get('limit', 50, type=int)
    history = signal_gen.get_history(limit)
    return jsonify(history)


@app.route('/api/refresh', methods=['POST'])
def refresh_signals():
    """Force refresh signals"""
    symbol = request.json.get('symbol', TRADING_PAIR)
    interval = request.json.get('interval', TIMEFRAME)

    signals = signal_gen.get_summary(symbol, interval)
    return jsonify({
        "success": True,
        **signals
    })


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=FLASK_PORT,
        debug=FLASK_DEBUG
    )