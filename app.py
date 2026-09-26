
import os
import time
import hmac
import hashlib
import json
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_USER_ID = str(os.environ["TELEGRAM_USER_ID"])
BYBIT_API_KEY = os.environ["BYBIT_API_KEY"]
BYBIT_API_SECRET = os.environ["BYBIT_API_SECRET"]

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
BYBIT_API = "https://api.bybit.com"

def tg(method, payload):
    r = requests.post(f"{TELEGRAM_API}/{method}", json=payload, timeout=20)
    r.raise_for_status()
    return r.json()

def send_message(chat_id, text, keyboard=True):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    if keyboard:
        payload["reply_markup"] = {
            "keyboard": [[{"text": "💰 Баланс"}, {"text": "📈 Позиции"}]],
            "resize_keyboard": True
        }
    return tg("sendMessage", payload)

def bybit_get(path, params=None):
    params = params or {}
    recv_window = "5000"
    timestamp = str(int(time.time() * 1000))
    query = "&".join(f"{k}={params[k]}" for k in sorted(params))
    to_sign = timestamp + BYBIT_API_KEY + recv_window + query
    signature = hmac.new(
        BYBIT_API_SECRET.encode(),
        to_sign.encode(),
        hashlib.sha256
    ).hexdigest()

    headers = {
        "X-BAPI-API-KEY": BYBIT_API_KEY,
        "X-BAPI-TIMESTAMP": timestamp,
        "X-BAPI-RECV-WINDOW": recv_window,
        "X-BAPI-SIGN": signature,
    }
    url = BYBIT_API + path
    r = requests.get(url, params=params, headers=headers, timeout=20)
    r.raise_for_status()
    data = r.json()
    if data.get("retCode") != 0:
        raise RuntimeError(f"{data.get('retCode')}: {data.get('retMsg')}")
    return data

def get_balance_text():
    data = bybit_get("/v5/account/wallet-balance", {"accountType": "UNIFIED"})
    accounts = data.get("result", {}).get("list", [])
    if not accounts:
        return "Баланс не найден."
    acc = accounts[0]
    total_wallet = acc.get("totalWalletBalance", "—")
    total_equity = acc.get("totalEquity", "—")
    total_available = acc.get("totalAvailableBalance", "—")

    coins = []
    for c in acc.get("coin", []):
        wallet = c.get("walletBalance")
        if wallet and wallet not in ("0", "0.0", ""):
            coins.append(f"• {c.get('coin')}: {wallet}")
    coin_text = "\n".join(coins[:20]) if coins else "Нет ненулевых монет."

    return (
        "<b>💰 Bybit Unified</b>\n"
        f"Equity: <b>{total_equity}</b> USD\n"
        f"Wallet: <b>{total_wallet}</b> USD\n"
        f"Доступно: <b>{total_available}</b> USD\n\n"
        f"{coin_text}"
    )

def get_positions_text():
    rows = []
    # Common derivatives categories. Ignore categories unavailable to the account.
    for category in ("linear", "inverse"):
        try:
            data = bybit_get("/v5/position/list", {"category": category, "settleCoin": "USDT"} if category == "linear" else {"category": category})
            rows.extend(data.get("result", {}).get("list", []))
        except Exception:
            pass

    active = []
    for p in rows:
        try:
            size = float(p.get("size") or 0)
        except Exception:
            size = 0
        if size != 0:
            active.append(p)

    if not active:
        return "📈 Открытых позиций не найдено."

    lines = ["<b>📈 Открытые позиции</b>"]
    for p in active[:20]:
        symbol = p.get("symbol", "—")
        side = p.get("side", "—")
        size = p.get("size", "—")
        avg = p.get("avgPrice", "—")
        mark = p.get("markPrice", "—")
        pnl = p.get("unrealisedPnl", "—")
        lev = p.get("leverage", "—")
        lines.append(
            f"\n<b>{symbol}</b> — {side}\n"
            f"Размер: {size} | x{lev}\n"
            f"Вход: {avg} | Mark: {mark}\n"
            f"PnL: {pnl}"
        )
    return "\n".join(lines)

@app.get("/")
def health():
    return "OK", 200

@app.post("/telegram")
def telegram_webhook():
    update = request.get_json(silent=True) or {}
    msg = update.get("message") or {}
    chat = msg.get("chat") or {}
    user = msg.get("from") or {}
    chat_id = chat.get("id")
    user_id = str(user.get("id", ""))
    text = (msg.get("text") or "").strip()

    if not chat_id:
        return jsonify(ok=True)

    if user_id != TELEGRAM_USER_ID:
        send_message(chat_id, "⛔ Этот бот приватный.", keyboard=False)
        return jsonify(ok=True)

    try:
        if text in ("/start", "/help"):
            send_message(
                chat_id,
                "🤖 <b>Bybit Assistant</b>\n\n"
                "Сейчас включён безопасный режим: только просмотр.\n"
                "Выбери действие ниже."
            )
        elif text == "💰 Баланс" or text == "/balance":
            send_message(chat_id, get_balance_text())
        elif text == "📈 Позиции" or text == "/positions":
            send_message(chat_id, get_positions_text())
        else:
            send_message(chat_id, "Используй кнопки «Баланс» или «Позиции».")
    except Exception as e:
        send_message(chat_id, f"⚠️ Ошибка: <code>{str(e)[:500]}</code>")
    return jsonify(ok=True)

@app.get("/set-webhook")
def set_webhook():
    base_url = request.host_url.rstrip("/")
    url = f"{base_url}/telegram"
    result = tg("setWebhook", {"url": url, "drop_pending_updates": True})
    return jsonify(result)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
