"""
Telegram bot entrypoint. Run with: python -m src.bot
Requires TELEGRAM_BOT_TOKEN in environment (e.g. from .env).
"""
import json
import logging
from pathlib import Path

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from src.config import load_config, setup_logging
from src.intent.parser import IntentParser
from src.security import SecurityManager

# Setup logging first
setup_logging()
logger = logging.getLogger(__name__)

# Load configuration
config = load_config()

# Constants
DEFAULT_SUPPORTED_SITES = "Printables and Thingiverse"
DEFAULT_MATERIAL = "PLA"
DEFAULT_COLOR = "black"
DEFAULT_PRICE = "free"
DEFAULT_QUEUE_POSITION = 1

# Global security manager
security_manager = SecurityManager()


def _supported_sites_message() -> str:
    """Load supported domains and return a human-readable list for messages."""
    path = Path(__file__).resolve().parent.parent / "config" / "supported_domains.json"
    if not path.exists():
        logger.warning("supported_domains.json not found, using default sites")
        return DEFAULT_SUPPORTED_SITES
    try:
        domains = json.loads(path.read_text(encoding="utf-8"))
        if not domains:
            return DEFAULT_SUPPORTED_SITES
        # "printables.com" -> "Printables", "thingiverse.com" -> "Thingiverse"
        names = [d.split(".")[0].capitalize() for d in domains if isinstance(d, str) and "." in d]
        return " and ".join(names) if names else DEFAULT_SUPPORTED_SITES
    except Exception as e:
        logger.error(f"Failed to load supported domains: {e}")
        return DEFAULT_SUPPORTED_SITES


def _log_user(update: Update, what: str) -> None:
    user = update.effective_user
    name = user.username or user.first_name or "?"
    logger.info("user message | user_id=%s @%s | %s", user.id, name, what)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _log_user(update, "/start")
    name = update.effective_user.first_name or update.effective_user.username or "there"
    await update.message.reply_text(
        f"Hi {name}! I'm Your3DPrintingBot — your 3D printing assistant. "
        f"Send me a link to Printables/Thingiverse and I'll print it for you. \n "
        f"Current material is {DEFAULT_MATERIAL}. \n Color: {DEFAULT_COLOR}. \n "
        f"Price: {DEFAULT_PRICE}. \nShipping: next time you see Jacek. "
        f"Position in queue: {DEFAULT_QUEUE_POSITION}."
    )


async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Parse user intent and reply based on parsed result."""
    text = update.message.text or ""
    user_id = update.effective_user.id
    _log_user(update, text)

    # Security checks
    is_allowed, error_msg = security_manager.check_security(user_id, text)
    if not is_allowed:
        logger.warning(f"Security check failed for user_id={user_id}: {error_msg}")
        await update.message.reply_text(f"Access denied: {error_msg}")
        return

    async with IntentParser() as parser:
        try:
            intent = await parser.parse(text)
            logger.info("intent parsed: %s", intent)
            if intent["intent"] == "unclear":
                sites = _supported_sites_message()
                await update.message.reply_text(
                    "I'm sorry, I didn't quite get that. I can only 3D print from "
                    f"{sites}. Send me a link and I'll let you know if I can print it.\\n\\n"
                    f"Current settings: material {DEFAULT_MATERIAL}, color {DEFAULT_COLOR}. "
                    f"Price: {DEFAULT_PRICE}. Shipping: next time you see Jacek. "
                    f"Position in queue: {DEFAULT_QUEUE_POSITION}."
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
    logger.info("Starting Your3DPrintingBot...")
    app = Application.builder().token(config.telegram_bot_token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_message))
    logger.info("Bot configured, starting polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
