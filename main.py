from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
import asyncio
from fastapi.responses import HTMLResponse

TOKEN = "8705414475:AAGJsY7sDIPapEyRtxC_fH3NEyivSX_h-N8"
WEBAPP_URL = "https://bd453a6e518d09.lhr.life"

bot = Bot(token=TOKEN)
dp = Dispatcher()

app = FastAPI()


# -------------------------
# LOGIC
# -------------------------
def message_wrapper(text: str, mode="send"):
    if mode == "send":
        return f"#LOL#{text}"
    if mode == "receive":
        return text.replace("#LOL#", "").strip()
    return text


# -------------------------
# BOT HANDLERS
# -------------------------
@dp.message()
async def handle_start(message: types.Message):
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
# SEND MESSAGE FROM WEBAPP
# -------------------------
@app.post("/send")
async def send_message(request: Request):
    data = await request.json()

    chat_id = data["chat_id"]
    text = data["text"]

    processed = message_wrapper(text, mode="send")

    await bot.send_message(chat_id, processed)

    return {"ok": True}


# -------------------------
# RECEIVE FROM TELEGRAM
# -------------------------
@app.post("/telegram")
async def telegram(request: Request):
    data = await request.json()
    print("GOT UPDATE:", data)
    update = types.Update(**data)
    await dp.feed_update(bot, update)
    return {"ok": True}