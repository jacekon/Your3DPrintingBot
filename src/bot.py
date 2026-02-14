"""
Telegram bot entrypoint. Run with: python -m src.bot
Requires TELEGRAM_BOT_TOKEN in environment (e.g. from .env).
"""
import os

from dotenv import load_dotenv

load_dotenv()

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Hi! I'm Your3DPrintingBot — your interface to the Elegoo Centauri Carbon. "
        "Send me a message or a link to Printables/Thingiverse and I'll help you out."
    )


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Placeholder: echo back. Replace with LLM + link handling pipeline."""
    await update.message.reply_text(f"You said: {update.message.text}")


def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN in environment (e.g. .env)")
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
