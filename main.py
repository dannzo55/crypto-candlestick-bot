#!/usr/bin/env python3

import argparse
import sys
from signal_generator import SignalGenerator
from config import TRADING_PAIR, TIMEFRAME

def main():
    parser = argparse.ArgumentParser(
        description='Crypto Candlestick Pattern Signal Bot'
    )
    parser.add_argument(
        '--symbol',
        default=TRADING_PAIR,
        help=f'Trading pair (default: {TRADING_PAIR})'
    )
    parser.add_argument(
        '--interval',
        default=TIMEFRAME,
        help=f'Timeframe (default: {TIMEFRAME})'
    )
    parser.add_argument(
        '--history',
        type=int,
        default=0,
        help='Show last N signals from history'
    )
    parser.add_argument(
        '--web',
        action='store_true',
        help='Start web dashboard'
    )
    
    args = parser.parse_args()
    
    signal_gen = SignalGenerator()
    
    if args.web:
        # Start web dashboard
        from app import app
        from config import FLASK_PORT
        print(f"Starting web dashboard on http://localhost:{FLASK_PORT}")
        app.run(debug=True)
    
    elif args.history > 0:
        # Show history
        history = signal_gen.get_history(args.history)
        print(f"\n=== Last {len(history)} Signals ===\n")
        for signal in history:
            print(f"Time: {signal['timestamp']}")
            print(f"Symbol: {signal['symbol']}")
            print(f"Price: {signal['current_price']}")
            print(f"Signals: {signal['signals_detected']}")
            print("-" * 50)
    
    else:
        # Generate current signals
        print(f"\n=== Signal Analysis ===")
        print(f"Symbol: {args.symbol}")
        print(f"Timeframe: {args.interval}\n")
        
        signals = signal_gen.get_summary(args.symbol, args.interval)
        
        if signals['success']:
            print(f"Current Price: ${signals['current_price']}")
            print(f"Last Candle: O:{signals['last_candle']['open']} "
                  f"H:{signals['last_candle']['high']} "
                  f"L:{signals['last_candle']['low']} "
                  f"C:{signals['last_candle']['close']}\n")
            
            print(f"Patterns Detected: {signals['signals_detected']}")
            print(f"  Buy Signals: {signals['buy_signals']}")
            print(f"  Sell Signals: {signals['sell_signals']}")
            print(f"  Neutral: {signals['neutral_signals']}\n")
            
            print(f"Recommendation: {signals['recommendation']}")
            print(f"Confidence: {signals['recommendation_confidence']}%\n")
            
            if signals['patterns']:
                print("Detected Patterns:")
                for pattern in signals['patterns']:
                    print(f"  - {pattern['pattern']}: {pattern['signal']} "
                          f"(Confidence: {pattern['confidence']}%)")
        else:
            print(f"Error: {signals.get('error', 'Unknown error')}")

if __name__ == '__main__':
    main()