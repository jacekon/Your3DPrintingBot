"""
Telegram bot entrypoint. Run with: python -m src.bot
Requires TELEGRAM_BOT_TOKEN in environment (e.g. from .env).
"""
import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from src.intent.parser import IntentParser


def _supported_sites_message() -> str:
    """Load supported domains and return a human-readable list for messages."""
    path = Path(__file__).resolve().parent.parent / "config" / "supported_domains.json"
    if not path.exists():
        return "Printables and Thingiverse"
    try:
        domains = json.loads(path.read_text(encoding="utf-8"))
        if not domains:
            return "Printables and Thingiverse"
        # "printables.com" -> "Printables", "thingiverse.com" -> "Thingiverse"
        names = [d.split(".")[0].capitalize() for d in domains if isinstance(d, str) and "." in d]
        return " and ".join(names) if names else "Printables and Thingiverse"
    except Exception:
        return "Printables and Thingiverse"

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def _log_user(update: Update, what: str) -> None:
    user = update.effective_user
    name = user.username or user.first_name or "?"
    logger.info("user message | user_id=%s @%s | %s", user.id, name, what)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _log_user(update, "/start")
    name = update.effective_user.first_name or update.effective_user.username or "there"
    await update.message.reply_text(
        f"Hi {name}! I'm Your3DPrintingBot — your 3D printing assistant. "
        "Send me a link to Printables/Thingiverse and I'll print it for you. \n Current material is PLA. \n Color: black. \n Price: free. \nShipping: next time you see Jacek. Position in queue: 1."
    )


async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Parse user intent and reply based on parsed result."""
    text = update.message.text or ""
    _log_user(update, text)

    parser = IntentParser()
    try:
        intent = await parser.parse(text)
        logger.info("intent parsed: %s", intent)
        if intent["intent"] == "unclear":
            sites = _supported_sites_message()
            await update.message.reply_text(
                "I'm sorry, I didn't quite get that. I can only 3D print from "
                f"{sites}. Send me a link and I'll let you know if I can print it.\n\n"
                "Current settings: material PLA, color black. Price: free. "
                "Shipping: next time you see Jacek. Position in queue: 1."
            )
        elif intent.get("error"):
            await update.message.reply_text(
                f"I understood: intent={intent['intent']}, confidence={intent['confidence']:.2f}. "
                f"Note: {intent['error']}"
            )
        else:
            await update.message.reply_text(
                f"Intent: {intent['intent']} (confidence: {intent['confidence']:.2f}). "
                f"Site: {intent.get('site') or '—'}, URL: {intent.get('url') or '—'}. "
                f"Material: {intent.get('material', 'PLA')}, color: {intent.get('color', 'printer_default')}."
            )
    except Exception as e:
        logger.exception("Intent parsing failed")
        await update.message.reply_text(f"Something went wrong while parsing your message: {e}")


def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN in environment (e.g. .env)")
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_message))
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
