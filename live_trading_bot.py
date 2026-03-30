import requests
import time
import numpy as np
import pandas as pd
from binance.client import Client
from binance.enums import *
import logging
from telegram import Bot

# Configure logging
logging.basicConfig(filename='trading_bot.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Binance and Telegram credentials
def get_credentials():
    return {'api_key': 'YOUR_BINANCE_API_KEY', 'api_secret': 'YOUR_BINANCE_API_SECRET', 'telegram_token': 'YOUR_TELEGRAM_TOKEN', 'telegram_chat_id': 'YOUR_TELEGRAM_CHAT_ID'}

# Initialize Binance client
credentials = get_credentials()
client = Client(credentials['api_key'], credentials['api_secret'])
telegram_bot = Bot(token=credentials['telegram_token'])

# Parameters
symbol = 'BNBUSDT'
short_window = 5
long_window = 20
rsi_period = 14
rsi_overbought = 70
rsi_oversold = 30
margin = 50

# Function to fetch historical data

def fetch_historical_data(symbol, interval, lookback):
    klines = client.get_historical_klines(symbol, interval, lookback)
    df = pd.DataFrame(klines, columns=['Open Time', 'Open', 'High', 'Low', 'Close', 'Volume', 'Close Time', 'Quote Asset Volume', 'Number of Trades', 'Taker Buy Base Asset Volume', 'Taker Buy Quote Asset Volume', 'Ignore'])
    df['Close'] = df['Close'].astype(float)
    return df

# MA Crossover and RSI strategy

def check_signals(df):
    df['Short MA'] = df['Close'].rolling(window=short_window).mean()
    df['Long MA'] = df['Close'].rolling(window=long_window).mean()
    df['RSI'] = calculate_rsi(df['Close'], rsi_period)
    buy_signal = (df['Short MA'].iloc[-2] < df['Long MA'].iloc[-2] and df['Short MA'].iloc[-1] > df['Long MA'].iloc[-1] and df['RSI'].iloc[-1] < rsi_oversold)
    sell_signal = (df['Short MA'].iloc[-2] > df['Long MA'].iloc[-2] and df['Short MA'].iloc[-1] < df['Long MA'].iloc[-1] and df['RSI'].iloc[-1] > rsi_overbought)
    return buy_signal, sell_signal

# RSI calculation

def calculate_rsi(series, period):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# Function to execute trades

def execute_trade(signal):
    global position
    if signal == 'buy' and position == 0:
        order = client.order_market_buy(symbol=symbol, quantity=0.1)  # Adjust quantity
        position = 1
        logging.info('Buy order executed')
        telegram_bot.send_message(chat_id=credentials['telegram_chat_id'], text='Buy order executed')
    elif signal == 'sell' and position == 1:
        order = client.order_market_sell(symbol=symbol, quantity=0.1)  # Adjust quantity
        position = 0
        logging.info('Sell order executed')
        telegram_bot.send_message(chat_id=credentials['telegram_chat_id'], text='Sell order executed')

# Main loop
position = 0

while True:
    df = fetch_historical_data(symbol, Client.KLINE_INTERVAL_1MINUTE, '1 day ago UTC')
    buy_signal, sell_signal = check_signals(df)
    if buy_signal:
        execute_trade('buy')
    elif sell_signal:
        execute_trade('sell')
    time.sleep(60)  # Wait for 1 minute before next check