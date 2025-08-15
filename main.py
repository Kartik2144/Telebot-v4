# main.py — start the bot and scheduler
import threading
import time
import logging

from src.telegram_bot import start_bot, info_log
from src.signal_engine import start_price_watcher, scheduled_scanner

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s - %(message)s")

if __name__ == "__main__":
    info_log("Starting CryptoChampsBot v4...")
    # Start Telegram polling (runs in background thread)
    start_bot()

    # Start price watcher thread (closes trades on TP/SL)
    threading.Thread(target=start_price_watcher, daemon=True).start()

    # Start scheduled scanner loop (blocking)
    scheduled_scanner()
