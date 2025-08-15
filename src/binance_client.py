# binance_client.py — CCXT wrappers for OHLCV and ticker
import ccxt
import time

EX = ccxt.binance({'enableRateLimit': True})

def fetch_ohlcv(symbol: str, timeframe: str, limit: int = 400):
    # symbol e.g. "YALA/USDT"
    for attempt in range(3):
        try:
            return EX.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        except Exception as e:
            if attempt == 2:
                raise
            time.sleep(1.5*(attempt+1))

def fetch_price(symbol: str):
    # returns last price float or None
    for attempt in range(3):
        try:
            t = EX.fetch_ticker(symbol)
            return float(t.get('last') or t.get('close') or 0.0)
        except Exception:
            time.sleep(0.8)
    return None
