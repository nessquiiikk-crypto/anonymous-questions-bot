import os
from aiohttp import web
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
PUBLIC_URL = os.getenv("PUBLIC_URL")

app = Application.builder().token(TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Напиши сюда сообщение — я анонимно передам его админу <3"
    )

async def forward_anonymous(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"📩 Анонимное сообщение:\n\n{text}"
    )

    await update.message.reply_text("Отправлено ✅")

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, forward_anonymous))

routes = web.RouteTableDef()

@routes.post("/webhook")
async def webhook(request: web.Request):
    data = await request.json()
    update = Update.de_json(data, app.bot)
    await app.process_update(update)
    return web.Response(text="ok")

@routes.get("/")
async def health(request: web.Request):
    return web.Response(text="alive")

async def on_startup(aioapp: web.Application):
    await app.initialize()

    if not PUBLIC_URL or not PUBLIC_URL.startswith("https://"):
        print("PUBLIC_URL is missing or not https. Skipping webhook setup.")
        return

    try:
        await app.bot.set_webhook(f"{PUBLIC_URL}/webhook")
        print("Webhook set successfully:", f"{PUBLIC_URL}/webhook")
    except Exception as e:
        print("Failed to set webhook:", e)


async def on_cleanup(aioapp: web.Application):
    await app.bot.delete_webhook()
    await app.shutdown()
    await app.stop()

def main():
    aioapp = web.Application()
    aioapp.add_routes(routes)
    aioapp.on_startup.append(on_startup)
    aioapp.on_cleanup.append(on_cleanup)

    port = int(os.getenv("PORT", "10000"))
    web.run_app(aioapp, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
