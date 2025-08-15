# signal_engine.py — scanner and watcher
import time, logging
from datetime import datetime
import pandas as pd

from src.config import PAIRS, TIMEFRAME, MAX_BARS, ATR_BREAK_K, ATR_LEN, VOL_SMA, EMA_FAST, EMA_SLOW, RSI_LEN, RSI_LONG, RSI_SHORT, in_active_window_ist, SCAN_INTERVAL_MINUTES, ATR_SL_MULT, ATR_TP_MULT
from src.binance_client import fetch_ohlcv, fetch_price
from src.indicators import add_indicators
from src.pnl_tracker import save_trade, get_open_trades, close_trade
# telegram helpers will be lazily imported inside functions to avoid circular import

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("signal_engine")

def _ohlcv_to_df(ohlcv):
    df = pd.DataFrame(ohlcv, columns=['ts','open','high','low','close','volume'])
    df['ts'] = pd.to_datetime(df['ts'], unit='ms')
    df[['open','high','low','close','volume']] = df[['open','high','low','close','volume']].astype(float)
    return df

def _check_signal_from_df(df, pair):
    # use last closed candle (index -2) to avoid current candle repaint
    if len(df) < 3:
        return None
    df = df.copy()
    df = add_indicators(df, ema_fast=EMA_FAST, ema_slow=EMA_SLOW, rsi_len=RSI_LEN, atr_len=ATR_LEN, vol_sma=VOL_SMA)
    last = df.iloc[-2]   # last closed
    prev = df.iloc[-3]   # previous closed
    # require indicators present
    if pd.isna(last['ema_fast']) or pd.isna(last['ema_slow']) or pd.isna(last['rsi']) or pd.isna(last['atr']) or pd.isna(last['vol_sma']):
        return None

    vol_ok = float(last['volume']) > float(last['vol_sma']) * 1.0

    long_break = prev['high'] + ATR_BREAK_K * last['atr']
    short_break = prev['low'] - ATR_BREAK_K * last['atr']

    # long condition
    if (last['ema_fast'] > last['ema_slow']) and (last['rsi'] >= RSI_LONG) and (last['close'] > long_break) and vol_ok:
        entry = float(last['close'])
        sl = entry - ATR_SL_MULT * float(last['atr'])
        tp = entry + ATR_TP_MULT * float(last['atr'])
        return {"pair": pair, "direction": "LONG", "entry": entry, "sl": sl, "tp": tp, "confidence": 75, "reason": "EMA trend + RSI + ATR breakout + vol"}

    # short condition
    if (last['ema_fast'] < last['ema_slow']) and (last['rsi'] <= RSI_SHORT) and (last['close'] < short_break) and vol_ok:
        entry = float(last['close'])
        sl = entry + ATR_SL_MULT * float(last['atr'])
        tp = entry - ATR_TP_MULT * float(last['atr'])
        return {"pair": pair, "direction": "SHORT", "entry": entry, "sl": sl, "tp": tp, "confidence": 75, "reason": "EMA trend down + RSI + ATR breakdown + vol"}

    return None

def scan_and_send_signals(forced=False):
    """
    Scan PAIRS and send signals. Returns number of signals sent.
    If forced=True, will scan even outside active window (used by /forcescan),
    but still respects safety checks.
    """
    sent = 0
    # lazy import telegram send function
    from src.telegram_bot import send_signal_msg, info_log

    if (not in_active_window_ist()) and (not forced):
        info_log("Scheduled scan skipped (outside IST window).")
        return 0

    for pair in PAIRS:
        try:
            ohlcv = fetch_ohlcv(pair, TIMEFRAME, limit=MAX_BARS)
            df = _ohlcv_to_df(ohlcv)
            sig = _check_signal_from_df(df, pair)
            if sig:
                # send to telegram
                try:
                    send_signal_msg(sig)
                except Exception as e:
                    info_log(f"Telegram send failed: {e}")
                # save to DB (open trade)
                try:
                    save_trade(sig['pair'], sig['direction'], sig['entry'], sig['sl'], sig['tp'])
                except Exception as e:
                    info_log(f"Save trade failed: {e}")
                sent += 1
        except Exception as e:
            info_log(f"Scan error for {pair}: {e}")

    return sent

def start_price_watcher(poll_seconds=30):
    """
    Background loop: checks open trades and closes them when TP/SL hit.
    Polling is frequent (default 30s) to pick TP/SL touches quickly.
    """
    from src.telegram_bot import send_exit_msg, info_log
    info_log("Price watcher started (TP/SL monitor).")
    while True:
        try:
            opens = get_open_trades()
            for tr in opens:
                pair = tr['pair']
                price = fetch_price(pair)
                if price is None:
                    continue
                # LONG
                if tr['direction'] == 'LONG':
                    if price >= tr['tp']:
                        pnl = tr['tp'] - tr['entry']
                        close_trade(tr['id'], 'TP', pnl)
                        send_exit_msg(tr, 'TP', pnl)
                    elif price <= tr['sl']:
                        pnl = tr['sl'] - tr['entry']
                        close_trade(tr['id'], 'SL', pnl)
                        send_exit_msg(tr, 'SL', pnl)
                # SHORT
                else:
                    if price <= tr['tp']:
                        pnl = tr['entry'] - tr['tp']
                        close_trade(tr['id'], 'TP', pnl)
                        send_exit_msg(tr, 'TP', pnl)
                    elif price >= tr['sl']:
                        pnl = tr['entry'] - tr['sl']
                        close_trade(tr['id'], 'SL', pnl)
                        send_exit_msg(tr, 'SL', pnl)
        except Exception as e:
            logger.exception("Watcher error: %s", e)
        time.sleep(poll_seconds)

def scheduled_scanner():
    """
    Main scheduled loop — runs indefinitely; triggers scan_and_send_signals()
    every SCAN_INTERVAL_MINUTES minutes but only during IST active window.
    """
    from src.telegram_bot import info_log
    info_log("Scheduler started. Scans every %s minutes (during IST active window)." % SCAN_INTERVAL_MINUTES)
    while True:
        try:
            if in_active_window_ist():
                info_log("Scheduled scan starting...")
                scan_and_send_signals()
            else:
                info_log("Outside IST active window — next check in 30s.")
        except Exception as e:
            logger.exception("Scheduled scan loop error: %s", e)
        time.sleep(SCAN_INTERVAL_MINUTES * 60)
