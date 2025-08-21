# config.py — main configuration
import os
from datetime import datetime, time as dtime
from zoneinfo import ZoneInfo

# Telegram (set as environment variables in Railway)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

# Pairs (strictly these)
PAIRS = ["YALA/USDT", "RUNE/USDT", "BTC/USDT", "ETH/USDT", "SOL/USDT"]

# Timeframe & cadence
TIMEFRAME = "15m"
SCAN_INTERVAL_MINUTES = int(os.getenv("SCAN_INTERVAL_MINUTES", "60"))  # 60 minutes

# Active window in IST: scans only between these times (inclusive start, exclusive end)
IST = ZoneInfo("Asia/Kolkata")
ACTIVE_START = dtime(7, 0)   # 07:00 IST
ACTIVE_END   = dtime(23, 0)  # 23:00 IST

def in_active_window_ist(dt=None):
    from datetime import datetime
    if dt is None:
        dt = datetime.now(IST)
    t = dt.time()
    return (t >= ACTIVE_START) and (t < ACTIVE_END)

# Strategy params
EMA_FAST = 20
EMA_SLOW = 50
RSI_LEN = 14
RSI_LONG = 53
RSI_SHORT = 47
ATR_LEN = 14
ATR_BREAK_K = 0.12
VOL_SMA = 20

ATR_SL_MULT = 1.3
ATR_TP_MULT = 1.8

# DB
DATA_DIR = os.path.join(os.getcwd(), "data")
DB_FILE = os.path.join(DATA_DIR, "trades.db")

# Data depth
MAX_BARS = 400
