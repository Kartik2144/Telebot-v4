# telegram_bot.py — telebot polling, commands, and message helper
import os, threading, logging
import telebot
from src.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, in_active_window_ist

LOG_PREFIX = "[Telegram]"
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("telegram_bot")

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, parse_mode=None) if TELEGRAM_BOT_TOKEN else None
CHAT_ID = TELEGRAM_CHAT_ID

def info_log(msg):
    logger.info(msg)
    print(msg, flush=True)

def safe_send(text):
    if not bot or not CHAT_ID:
        info_log("Telegram not configured (missing token/chat id).")
        return
    try:
        bot.send_message(CHAT_ID, text)
    except Exception as e:
        info_log(f"Telegram send error: {e}")

def send_signal_msg(sig):
    # sig is dict with pair,direction,entry,sl,tp,confidence,reason
    txt = (
        f"📈 Signal — {sig['pair']}\n"
        f"📍DIRECTION: {sig['direction']}\n"
        f"🚀Entry: {sig['entry']}\n"
        f"🎯Target: {sig['tp']}\n"
        f"⛔Stop Loss: {sig['sl']}\n"
        f"🤖Confidence: {sig.get('confidence', 70)}%\n"
        f"®️Reason: {sig.get('reason','')}"
    )
    safe_send(txt)

def send_exit_msg(trade, status, pnl):
    txt = (
        f"❇️ Exit — {trade['pair']} ({status})\n"
        f"Direction: {trade['direction']}\n"
        f"Entry: {trade['entry']}\n"
        f"TP: {trade['tp']}\n"
        f"SL: {trade['sl']}\n"
        f"🅿️PnL: {round(pnl,6)}"
    )
    safe_send(txt)

# Commands
if bot:
    @bot.message_handler(commands=['start'])
    def start_cmd(m):
        bot.reply_to(m, "🤖 CryptoChamps v4 online. Commands: /testsignal /pnl /forcescan")

    @bot.message_handler(commands=['testsignal'])
    def testsignal_cmd(m):
        demo = {
            "pair":"YALA/USDT","direction":"LONG","entry":0,"sl":0,"tp":0,"confidence":75,"reason":"demo"
        }
        bot.reply_to(m, "✅ Test OK. Bot running. (no real trade placed)")

    @bot.message_handler(commands=['pnl'])
    def pnl_cmd(m):
        try:
            from src.pnl_tracker import todays_trades
            rows = todays_trades()
            if not rows:
                bot.reply_to(m, "📊 No trades today.")
                return
            lines = ["📊 Today's trades (UTC):"]
            net = 0.0
            for r in rows:
                pnl = r.get('pnl') or 0.0
                net += pnl
                lines.append(f"{r['pair']} | {r['direction']} | {r['status']} | PnL: {round(pnl,6)}")
            lines.append(f"\n💰 Net PnL: {round(net,6)}")
            bot.reply_to(m, "\n".join(lines))
        except Exception as e:
            bot.reply_to(m, f"Error fetching PnL: {e}")

    @bot.message_handler(commands=['forcescan'])
    def forcescan_cmd(m):
        if not in_active_window_ist():
            bot.reply_to(m, "⏸️ Outside active IST window (07:00–23:00). Scan skipped.")
            return
        # lazy import to avoid circulars
        from src.signal_engine import scan_and_send_signals
        try:
            cnt = scan_and_send_signals(forced=True)
            bot.reply_to(m, f"🔎 Force scan complete. Signals sent: {cnt}")
        except Exception as e:
            bot.reply_to(m, f"Force scan error: {e}")

def start_bot():
    # Remove webhook and start polling in background thread
    if not bot:
        info_log("TELEGRAM_BOT_TOKEN missing; Telegram bot not started.")
        return
    try:
        bot.delete_webhook()
        info_log("✅ Webhook deleted (polling enabled)")
    except Exception:
        pass
    threading.Thread(target=lambda: bot.polling(non_stop=True, interval=0, timeout=20), daemon=True).start()
    info_log("🚀 Telegram polling started")
