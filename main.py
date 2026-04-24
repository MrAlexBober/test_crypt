from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
import asyncio
import time

TOKEN = "8705414475:AAGJsY7sDIPapEyRtxC_fH3NEyivSX_h-N8"
WEBAPP_URL = "https://testcrypt-production.up.railway.app"

bot = Bot(token=TOKEN)
dp = Dispatcher()

app = FastAPI()

# chat_id -> {username, first_name, last_seen}
online_users = {}

ONLINE_TIMEOUT = 30  # секунд без пинга — считаем офлайн

# chat_id -> [{"from_id": ..., "text": ...}, ...]
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
    online_users[chat_id] = {
        "username": data.get("username", ""),
        "first_name": data.get("first_name", ""),
        "last_seen": time.time()
    }
    return {"ok": True}


@app.post("/online/ping")
async def online_ping(request: Request):
    data = await request.json()
    chat_id = str(data["chat_id"])
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
# SEND MESSAGE
# -------------------------
@app.post("/send")
async def send_message(request: Request):
    data = await request.json()
    to_id = str(data["to_id"])
    from_id = str(data["from_id"])
    payload = data["payload"]  # {type: "dh_init"|"dh_response"|"msg", ...}

    if to_id not in inbox:
        inbox[to_id] = []
    inbox[to_id].append({"from_id": from_id, "payload": payload})

    if payload.get("type") == "msg":
        await bot.send_message(to_id, "🔒 Новое зашифрованное сообщение")

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
