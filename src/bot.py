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
from src.downloads.fetcher import fetch_model_files
from src.intent.parser import IntentParser
from src.security import SecurityManager
from src.slicer import OrcaSlicer

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
        f"Send me a link to Printables and I'll print it for you. \n "
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
                    f"{sites}. Send me a link and I'll let you know if I can print it.\n"
                    f"Current settings:\nmaterial {DEFAULT_MATERIAL},\ncolor {DEFAULT_COLOR}.\n"
                    f"Price: {DEFAULT_PRICE}.\nShipping: next time you see Jacek.\n"
                    f"Position in queue: {DEFAULT_QUEUE_POSITION}."
                )
            elif intent.get("error"):
                await update.message.reply_text(
                    f"I understood: intent={intent['intent']}, confidence={intent['confidence']:.2f}. "
                    f"Note: {intent['error']}"
                )
            elif intent["intent"] == "print":
                # User wants to print - download files
                url = intent.get("url")
                site = intent.get("site")
                if not url:
                    await update.message.reply_text(
                        "I understand you want to print something, but I couldn't find a valid link. "
                        "Please send me a link from Printables or Thingiverse."
                    )
                else:
                    await update.message.reply_text(
                        f"Got it! Downloading files from {site or 'the link'}... ⏳"
                    )
                    try:
                        job_id, stl_paths = await fetch_model_files(url, user_id=user_id)
                        if stl_paths:
                            file_list = "\n".join([f"  • {p.name}" for p in stl_paths[:5]])
                            if len(stl_paths) > 5:
                                file_list += f"\n  ... and {len(stl_paths) - 5} more"
                            output_dir = stl_paths[0].parent
                            await update.message.reply_text(
                                f"✅ Downloaded {len(stl_paths)} file(s) for printing!\n"
                                f"Job ID: {job_id}\n\n"
                                f"Files:\n{file_list}\n\n"
                                f"Material: {intent.get('material', 'PLA')}, Color: {intent.get('color', 'printer_default')}\n"
                                f"Position in queue: {DEFAULT_QUEUE_POSITION}\n\n"
                            )
                            try:
                                slicer = OrcaSlicer()
                                gcode_paths = await slicer.slice_files(stl_paths, output_dir)
                                gcode_list = "\n".join([f"  • {p.name}" for p in gcode_paths[:5]])
                                if len(gcode_paths) > 5:
                                    gcode_list += f"\n  ... and {len(gcode_paths) - 5} more"
                                await update.message.reply_text(
                                    f"✅ Sliced {len(gcode_paths)} file(s)!\n"
                                    f"G-code files:\n{gcode_list}"
                                )
                            except Exception as e:
                                logger.exception("Slicing failed")
                                await update.message.reply_text(
                                    f"❌ Slicing failed: {e}"
                                )
                                return

                            await update.message.reply_text("⏳ Uploading G-code to the printer...")
                            #todo
                        else:
                            await update.message.reply_text(
                                f"⚠️ No STL files found at {url}. Please check the link and try again."
                            )
                    except NotImplementedError:
                        await update.message.reply_text(
                            f"Sorry, downloading from {site} is not yet supported. "
                            "Currently only Printables.com is supported."
                        )
                    except Exception as e:
                        logger.exception(f"Failed to download files from {url}")
                        await update.message.reply_text(
                            f"❌ Failed to download files: {str(e)}\n\n"
                            "Please check the link and try again."
                        )
            elif intent["intent"] == "save":
                # User wants to save for later
                url = intent.get("url")
                site = intent.get("site") or "the link"
                if url:
                    await update.message.reply_text(
                        f"📌 Noted! I've saved this {site} model for later.\n"
                        f"Link: {url}\n\n"
                        "(Note: Bookmark feature is not fully implemented yet - "
                        "this is just a confirmation message)"
                    )
                else:
                    await update.message.reply_text(
                        "I understand you want to save something, but I couldn't find a link. "
                        "Please send me a link to save."
                    )
            elif intent["intent"] == "info":
                # User wants information
                url = intent.get("url")
                site = intent.get("site") or "the link"
                if url:
                    await update.message.reply_text(
                        f"ℹ️ Information about this {site} model:\n"
                        f"Link: {url}\n\n"
                        "(Note: Detailed model info fetching is not fully implemented yet - "
                        "you can visit the link to see details)"
                    )
                else:
                    await update.message.reply_text(
                        "I understand you want information, but I couldn't find what you're asking about. "
                        "Please send me a link to a model."
                    )
            else:
                # Fallback for any other intent
                await update.message.reply_text(
                    f"Intent detected: {intent['intent']} (confidence: {intent['confidence']:.2f})\n"
                    f"Site: {intent.get('site') or '—'}, URL: {intent.get('url') or '—'}"
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
