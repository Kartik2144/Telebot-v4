# pnl_tracker.py — full trade logging to sqlite
import os, sqlite3
from datetime import datetime, timezone
from src.config import DATA_DIR, DB_FILE

os.makedirs(DATA_DIR, exist_ok=True)

def _conn():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = _conn(); c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pair TEXT,
        direction TEXT,
        entry REAL,
        sl REAL,
        tp REAL,
        status TEXT DEFAULT 'OPEN',
        pnl REAL DEFAULT 0,
        created_at TEXT,
        closed_at TEXT
    )
    """)
    conn.commit(); conn.close()

def save_trade(pair, direction, entry, sl, tp):
    conn = _conn(); c = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()
    c.execute("INSERT INTO trades (pair, direction, entry, sl, tp, status, created_at) VALUES (?, ?, ?, ?, ?, 'OPEN', ?)",
              (pair, direction, float(entry), float(sl), float(tp), now))
    conn.commit()
    trade_id = c.lastrowid
    conn.close()
    return trade_id

def close_trade(trade_id, status, pnl):
    conn = _conn(); c = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()
    c.execute("UPDATE trades SET status=?, pnl=?, closed_at=? WHERE id=?", (status, float(pnl), now, trade_id))
    conn.commit(); conn.close()

def get_open_trades():
    conn = _conn(); c = conn.cursor()
    rows = c.execute("SELECT * FROM trades WHERE status='OPEN'").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def todays_trades():
    conn = _conn(); c = conn.cursor()
    today = datetime.now(timezone.utc).date().isoformat()
    rows = c.execute("SELECT pair, direction, status, pnl, created_at FROM trades WHERE created_at LIKE ? ORDER BY id DESC", (f"{today}%",)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ensure DB exists on import
init_db()
