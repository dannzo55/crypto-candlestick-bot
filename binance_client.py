from binance.client import Client
import pandas as pd
from config import BINANCE_API_KEY, BINANCE_API_SECRET

class BinanceClient:
    """Handles all Binance API interactions"""
    
    def __init__(self):
        """Initialize Binance client"""
        self.client = Client(BINANCE_API_KEY, BINANCE_API_SECRET)
    
    def get_historical_data(self, symbol, interval, limit=500):
        """
        Fetch historical candlestick data from Binance
        
        Args:
            symbol: Trading pair (e.g., 'ETHUSDT')
            interval: Timeframe (e.g., '15m', '1h')
            limit: Number of candles to fetch
        
        Returns:
            pandas DataFrame with OHLCV data
        """
        try:
            klines = self.client.get_historical_klines(
                symbol, 
                interval, 
                limit=limit
            )
            
            df = pd.DataFrame(klines, columns=[
                'open_time',
                'open',
                'high',
                'low',
                'close',
                'volume',
                'close_time',
                'quote_asset_volume',
                'number_of_trades',
                'taker_buy_base_asset_volume',
                'taker_buy_quote_asset_volume',
                'ignore'
            ])
            
            # Convert to numeric and datetime
            df['open'] = pd.to_numeric(df['open'])
            df['high'] = pd.to_numeric(df['high'])
            df['low'] = pd.to_numeric(df['low'])
            df['close'] = pd.to_numeric(df['close'])
            df['volume'] = pd.to_numeric(df['volume'])
            df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
            
            return df[['open_time', 'open', 'high', 'low', 'close', 'volume']]
        
        except Exception as e:
            print(f"Error fetching historical data: {e}")
            return None
    
    def get_latest_price(self, symbol):
        """Get current price of a symbol"""
        try:
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            return float(ticker['price'])
        except Exception as e:
            print(f"Error fetching price for {symbol}: {e}")
            return None
    
    def get_account_balance(self):
        """Get account balance"""
        try:
            account = self.client.get_account()
            return account
        except Exception as e:
            print(f"Error fetching account balance: {e}")
            return None
    
    def get_exchange_info(self):
        """Get exchange information"""
        try:
            return self.client.get_exchange_info()
        except Exception as e:
            print(f"Error fetching exchange info: {e}")
            return None
