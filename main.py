import os
import logging
from aiohttp import web

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ---- logging (чтоб не светить лишнее) ----
logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)

# ---- env ----
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
PUBLIC_URL = os.getenv("PUBLIC_URL")

# ---- bot handlers ----
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Напиши сюда сообщение — я анонимно передам его админу <3"
    )

async def forward_anonymous(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text

    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"📩 Анонимное сообщение:\n\n{text}"
    )

    await update.message.reply_text("Отправлено ✅")

async def error_handler(update, context: ContextTypes.DEFAULT_TYPE):
    logging.exception("Unhandled error", exc_info=context.error)

# ---- create telegram application ----
tg_app = Application.builder().token(TOKEN).build()
tg_app.add_handler(CommandHandler("start", start_cmd))
tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, forward_anonymous))
tg_app.add_error_handler(error_handler)

# ---- aiohttp routes ----
routes = web.RouteTableDef()

@routes.get("/")
async def health(request: web.Request):
    return web.Response(text="alive")

@routes.post("/webhook")
async def webhook(request: web.Request):
    data = await request.json()
    update = Update.de_json(data, tg_app.bot)
    await tg_app.process_update(update)
    return web.Response(text="ok")

# ---- lifecycle ----
async def on_startup(aioapp: web.Application):
    if not TOKEN or not ADMIN_ID:
        raise RuntimeError("BOT_TOKEN or ADMIN_ID is missing in environment variables")

    await tg_app.initialize()
    await tg_app.start()

    # Ставим webhook только если PUBLIC_URL нормальный
    if PUBLIC_URL and PUBLIC_URL.startswith("https://"):
        try:
            await tg_app.bot.set_webhook(f"{PUBLIC_URL}/webhook")
            print("Webhook set:", f"{PUBLIC_URL}/webhook")
        except Exception as e:
            print("Failed to set webhook:", e)
    else:
        print("PUBLIC_URL missing/invalid, skipping webhook setup")

async def on_cleanup(aioapp: web.Application):
    try:
        await tg_app.bot.delete_webhook()
    except Exception:
        pass

    await tg_app.stop()
    await tg_app.shutdown()

def main():
    aioapp = web.Application()
    aioapp.add_routes(routes)
    aioapp.on_startup.append(on_startup)
    aioapp.on_cleanup.append(on_cleanup)
