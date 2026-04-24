from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
import time
import json
import os

TOKEN = os.environ.get("TOKEN", "YOUR_BOT_TOKEN_HERE")
WEBAPP_URL = os.environ.get("WEBAPP_URL", "https://testcrypt-production.up.railway.app")

bot = Bot(token=TOKEN)
dp = Dispatcher()
app = FastAPI()

# username (lowercase) -> chat_id
known_users = {}

# online presence: chat_id -> {username, first_name, last_seen}
online_users = {}
ONLINE_TIMEOUT = 30

# входящие dh_init: to_id -> [{from_id, from_name, pubkey, timestamp, expires_in}]
pending_dh = {}

# временный буфер сообщений: chat_id -> [...]
inbox = {}


def get_online_list():
    now = time.time()
    alive = {k: v for k, v in online_users.items() if now - v["last_seen"] < ONLINE_TIMEOUT}
    online_users.clear()
    online_users.update(alive)
    return [{"chat_id": k, **v} for k, v in alive.items()]


# -------------------------
# BOT HANDLERS
# -------------------------
@dp.message()
async def handle_message(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Open Chat", web_app=WebAppInfo(url=WEBAPP_URL))
    ]])
    await message.answer("Открой чат:", reply_markup=keyboard)


# -------------------------
# WEBAPP PAGE
# -------------------------
@app.get("/", response_class=HTMLResponse)
def home():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()


# -------------------------
# ONLINE PRESENCE
# -------------------------
@app.post("/online/join")
async def online_join(request: Request):
    data = await request.json()
    chat_id = str(data["chat_id"])
    username = data.get("username", "")
    online_users[chat_id] = {
        "username": username,
        "first_name": data.get("first_name", ""),
        "last_seen": time.time()
    }
    if username:
        known_users[username.lower()] = chat_id
    return {"ok": True}


@app.post("/online/ping")
async def online_ping(request: Request):
    data = await request.json()
    chat_id = str(data.get("chat_id", ""))
    if not chat_id or chat_id == "None" or chat_id == "undefined":
        return {"ok": False}
    if chat_id in online_users:
        online_users[chat_id]["last_seen"] = time.time()
    return {"ok": True}


@app.post("/online/leave")
async def online_leave(request: Request):
    data = await request.json()
    chat_id = str(data["chat_id"])
    online_users.pop(chat_id, None)
    return {"ok": True}


@app.get("/online/list")
async def online_list():
    return JSONResponse(get_online_list())


# -------------------------
# RESOLVE USERNAME
# -------------------------
@app.get("/resolve")
async def resolve_username(username: str):
    clean = username.lower().lstrip("@")
    chat_id = known_users.get(clean)
    if not chat_id:
        return JSONResponse({"ok": False, "error": "User not found. Ask them to open the bot first."})
    return JSONResponse({"ok": True, "chat_id": chat_id})


@app.get("/search")
async def search_users(q: str):
    q = q.lower().lstrip("@")
    if not q:
        return JSONResponse([])
    matches = [
        {"username": uname, "chat_id": cid}
        for uname, cid in known_users.items()
        if q in uname
    ][:10]
    return JSONResponse(matches)


# -------------------------
# SESSION: INIT (отправить запрос на сессию)
# -------------------------
@app.post("/session/init")
async def session_init(request: Request):
    data = await request.json()
    to_id = str(data["to_id"])
    from_id = str(data["from_id"])
    from_name = data.get("from_name", "Кто-то")
    pubkey = data["pubkey"]
    expires_in = data.get("expires_in")  # секунды или null

    if to_id not in pending_dh:
        pending_dh[to_id] = []

    # Убираем предыдущий запрос от того же отправителя
    pending_dh[to_id] = [p for p in pending_dh[to_id] if p["from_id"] != from_id]
    pending_dh[to_id].append({
        "from_id": from_id,
        "from_name": from_name,
        "pubkey": pubkey,
        "timestamp": time.time(),
        "expires_in": expires_in
    })

    await bot.send_message(
        to_id,
        f"🔐 <b>{from_name}</b> хочет начать зашифрованный чат.\nОткройте WebApp чтобы принять.",
        parse_mode="HTML"
    )
    return {"ok": True}


# -------------------------
# SESSION: PENDING (получить входящие запросы)
# -------------------------
@app.get("/session/pending")
async def session_pending(chat_id: str):
    return JSONResponse(pending_dh.get(chat_id, []))


# -------------------------
# SESSION: RESPOND (принять сессию)
# -------------------------
@app.post("/session/respond")
async def session_respond(request: Request):
    data = await request.json()
    to_id = str(data["to_id"])      # инициатор
    from_id = str(data["from_id"])  # принимающий
    from_name = data.get("from_name", "Собеседник")
    pubkey = data["pubkey"]

    # Кладём dh_response в inbox инициатора
    if to_id not in inbox:
        inbox[to_id] = []
    inbox[to_id].append({
        "from_id": from_id,
        "payload": {"type": "dh_response", "pubkey": pubkey, "from_name": from_name}
    })

    # Убираем из pending получателя (from_id), где инициатор = to_id
    if from_id in pending_dh:
        pending_dh[from_id] = [p for p in pending_dh[from_id] if p["from_id"] != to_id]

    await bot.send_message(
        to_id,
        f"✅ <b>{from_name}</b> принял(а) запрос на зашифрованный чат.",
        parse_mode="HTML"
    )
    return {"ok": True}


# -------------------------
# SESSION: DECLINE
# -------------------------
@app.post("/session/decline")
async def session_decline(request: Request):
    data = await request.json()
    to_id = str(data["to_id"])
    from_id = str(data["from_id"])
    if to_id in pending_dh:
        pending_dh[to_id] = [p for p in pending_dh[to_id] if p["from_id"] != from_id]
    return {"ok": True}


# -------------------------
# SESSION: CLOSE
# -------------------------
@app.post("/session/close")
async def session_close(request: Request):
    data = await request.json()
    to_id = str(data["to_id"])
    from_id = str(data["from_id"])
    from_name = data.get("from_name", "Собеседник")

    if to_id not in inbox:
        inbox[to_id] = []
    inbox[to_id].append({
        "from_id": from_id,
        "payload": {"type": "session_closed", "from_name": from_name}
    })

    await bot.send_message(
        to_id,
        f"🔒 <b>{from_name}</b> закрыл(а) сессию.",
        parse_mode="HTML"
    )
    return {"ok": True}


# -------------------------
# SEND ENCRYPTED MESSAGE
# -------------------------
@app.post("/send")
async def send_message(request: Request):
    data = await request.json()
    to_id = str(data["to_id"])
    from_id = str(data["from_id"])
    payload = data["payload"]

    if to_id not in inbox:
        inbox[to_id] = []
    inbox[to_id].append({"from_id": from_id, "payload": payload})

    # Шифротекст виден в Telegram чате для прозрачности
    ct = payload.get("ciphertext", "")[:40]
    await bot.send_message(to_id, f"🔒 <code>{ct}...</code>", parse_mode="HTML")

    return {"ok": True}


# -------------------------
# POLL MESSAGES
# -------------------------
@app.get("/messages/poll")
async def poll_messages(chat_id: str):
    msgs = inbox.pop(chat_id, [])
    return JSONResponse(msgs)


# -------------------------
# RECEIVE FROM TELEGRAM
# -------------------------
@app.post("/telegram")
async def telegram(request: Request):
    data = await request.json()
    update = types.Update(**data)
    await dp.feed_update(bot, update)
    return {"ok": True}
