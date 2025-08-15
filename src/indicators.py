# indicators.py — pandas-based indicators
import pandas as pd
import numpy as np

def ema(series: pd.Series, length: int):
    return series.ewm(span=length, adjust=False).mean()

def rsi(series: pd.Series, length: int = 14):
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    ma_up = up.ewm(alpha=1/length, adjust=False).mean()
    ma_down = down.ewm(alpha=1/length, adjust=False).mean()
    rs = ma_up / (ma_down + 1e-9)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)

def atr(df: pd.DataFrame, length: int = 14):
    high = df['high']; low = df['low']; close = df['close']
    prev_close = close.shift(1)
    tr = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    return tr.ewm(span=length, adjust=False).mean()

def add_indicators(df, ema_fast=20, ema_slow=50, rsi_len=14, atr_len=14, vol_sma=20):
    df = df.copy()
    df['ema_fast'] = ema(df['close'], ema_fast)
    df['ema_slow'] = ema(df['close'], ema_slow)
    df['rsi'] = rsi(df['close'], rsi_len)
    df['atr'] = atr(df, atr_len)
    df['vol_sma'] = df['volume'].rolling(vol_sma).mean()
    return df
