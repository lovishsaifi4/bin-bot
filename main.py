import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Route
import asyncio
import logging
import random
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
TOKEN = os.getenv("TOKEN", "7881163673:AAGgNQwfX6MYMAyOKLrdZkp2hoDCLUa4OEU")
BIN_API_URL = "https://api.api-ninjas.com/v1/bin?bin={}"
API_KEY = "lQiHO34dFj8jY4xYNacj3g==oyNatSR2JdLDlWLw"
WEBHOOK_URL = os.getenv("RENDER_EXTERNAL_URL", f"https://bin-bot-kqa8.onrender.com") + f"/{TOKEN}"

# Luhn algorithm for CC generation
def luhn_checksum(card_number):
    def digits_of(n):
        return [int(d) for d in str(n)]
    digits = digits_of(card_number)
    odd_digits = digits[-1::-2]
    even_digits = digits[-2::-2]
    checksum = sum(odd_digits)
    for d in even_digits:
        checksum += sum(digits_of(d * 2))
    return checksum % 10

def generate_cc(bin_number, count=10):
    bin_number = bin_number[:6]
    generated_cards = []
    current_year = datetime.now().year
    for _ in range(count):
        remaining = ''.join([str(random.randint(0, 9)) for _ in range(10)])
        card = bin_number + remaining
        check_sum = luhn_checksum(int(card + "0"))
        check_digit = (10 - check_sum) % 10
        full_card = card + str(check_digit)
        
        month = f"{random.randint(1, 12):02d}"
        year = str(random.randint(current_year + 1, current_year + 5))
        cvv = f"{random.randint(0, 999):03d}"
        
        generated_cards.append(f"{full_card}|{month}|{year}|{cvv}")
    return generated_cards

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    welcome_message = (
        "Welcome 🔥\n"
        "✨This bot was created by @Hellfirez3643\n"
        "🤩This bot can generate cards and check bins.\n"
        "✅Use .gen for generating cards. Format : .gen 424242\n"
        "✅Use .bin for getting bin info. Format: .bin 424242\n"
        "⚠️Join @VengeanceSeekers for future projects and updates. We have something you can even imagine and something you will remain unaware of forever."
    )
    await update.message.reply_text(welcome_message)

async def check_bin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("❌ Please provide a BIN number. Usage: /bin <BIN>")
        return
    bin_number = context.args[0][:6]
    await process_bin(update, bin_number)

async def check_bin_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message_text = update.message.text
    if message_text.startswith(".bin"):
        bin_number = message_text.replace(".bin", "").strip()[:6]
        if not (bin_number.isdigit() and len(bin_number) >= 6):
            await update.message.reply_text("❌ Invalid BIN. Use .bin followed by a 6-digit number.")
            return
        await process_bin(update, bin_number)

async def generate_cc_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("❌ Please provide a BIN number. Usage: /gen <BIN>")
        return
    bin_number = context.args[0][:6]
    await generate_cc_process(update, bin_number)

async def generate_cc_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message_text = update.message.text
    if message_text.startswith(".gen"):
        bin_number = message_text.replace(".gen", "").strip()[:6]
        if not (bin_number.isdigit() and len(bin_number) >= 6):
            await update.message.reply_text("❌ Invalid BIN. Use .gen followed by a 6-digit number.")
            return
        await generate_cc_process(update, bin_number)

async def process_bin(update: Update, bin_number: str) -> None:
    try:
        headers = {"X-Api-Key": API_KEY}
        response = requests.get(BIN_API_URL.format(bin_number), headers=headers, timeout=5)
        response.raise_for_status()
        data = response.json()[0]
        logger.info(f"API Response for BIN {bin_number}: {data}")

        def escape_md(text):
            if not text:
                return "Unknown"
            chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
            for char in chars:
                text = str(text).replace(char, f'\{char}')
            return text

        brand = escape_md(data.get("brand", "Unknown")).capitalize()
        type_ = escape_md(data.get("type", "Unknown")).capitalize()
        bank = escape_md(data.get("bank", "Unknown"))
        country_name = escape_md(data.get("country", "Unknown"))
        country_code = data.get("country_code", "??").lower()

        flag = "".join([chr(0x1F1E6 + ord(c) - ord('a')) for c in country_code]) if country_code != "??" else "🌐"

        message = (
            f"```\n"
            f"📒 *BIN*: {bin_number}\n"
            f"🏷️ *Card Brand*: {brand}\n"
            f"💳 *Card Type*: {type_}\n"
            f"🏦 *Bank*: {bank}\n"
            f"{flag} *Country*: {country_name}\n"
            f"✅ *Bot by*: @Hellfirez3643\n"
            f"```\n"  # Ensure closing triple backticks
        )
        await update.message.reply_text(message, parse_mode="MarkdownV2")
    except requests.Timeout:
        await update.message.reply_text("⏳ Request timed out. Please try again later.")
    except requests.RequestException as e:
        if response.status_code == 429:
            await update.message.reply_text("⏱️ Rate limit reached. Please wait and try again.")
        else:
            await update.message.reply_text(f"❌ Error checking BIN: {str(e)}")
    except (ValueError, IndexError):
        await update.message.reply_text("❌ Invalid response from BIN API or BIN not found.")
    except Exception as e:
        await update.message.reply_text(f"❌ Unexpected error: {str(e)}")

async def generate_cc_process(update: Update, bin_number: str) -> None:
    try:
        if not bin_number.isdigit() or len(bin_number) < 6:
            await update.message.reply_text("❌ Invalid BIN. Please provide a 6-digit number.")
            return
        
        # Fetch country info from API
        headers = {"X-Api-Key": API_KEY}
        response = requests.get(BIN_API_URL.format(bin_number), headers=headers, timeout=5)
        response.raise_for_status()
        data = response.json()[0]
        logger.info(f"API Response for BIN {bin_number} (gen): {data}")

        def escape_md(text):
            if not text:
                return "Unknown"
            chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
            for char in chars:
                text = str(text).replace(char, f'\{char}')
            return text

        country_name = escape_md(data.get("country", "Unknown"))
        country_code = data.get("country_code", "??").lower()
        flag = "".join([chr(0x1F1E6 + ord(c) - ord('a')) for c in country_code]) if country_code != "??" else "🌐"

        # Generate CC numbers
        cc_numbers = generate_cc(bin_number, count=10)

        message = (
            f"```\n"
            f"📒 *BIN*: {escape_md(bin_number)}\n"
            f"{flag} *Country*: {country_name}\n"
            f"💳 *Generated CC Numbers*:\n" +
            "\n".join([f"  • {escape_md(cc)}" for cc in cc_numbers]) + "\n"
            f"✅ *Bot by*: @Hellfirez3643\n"
            f"```\n"  # Ensure closing triple backticks
        )
        await update.message.reply_text(message, parse_mode="MarkdownV2")
    except requests.Timeout:
        await update.message.reply_text("⏳ Request timed out. Please try again later.")
    except requests.RequestException as e:
        if response.status_code == 429:
            await update.message.reply_text("⏱️ Rate limit reached. Please wait and try again.")
        else:
            await update.message.reply_text(f"❌ Error generating CC: {str(e)}")
    except (ValueError, IndexError):
        await update.message.reply_text("❌ Invalid response from BIN API or BIN not found.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error generating CC: {str(e)}")

# Webhook handler
async def webhook(request: Request) -> Response:
    update = Update.de_json(await request.json(), application.bot)
    if update:
        await application.process_update(update)
    return Response(status_code=200)

# Health check endpoint
async def health(request: Request) -> Response:
    return Response(content="OK", status_code=200)

# Application setup
application = Application.builder().token(TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("bin", check_bin_command))
application.add_handler(CommandHandler("gen", generate_cc_command))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, lambda update, context: check_bin_message(update, context) if update.message.text.startswith(".bin") else generate_cc_message(update, context)))

# Startup and shutdown for Starlette
async def startup():
    await application.initialize()
    await application.start()
    await application.bot.setWebhook(url=WEBHOOK_URL)
    logger.info(f"Webhook set to {WEBHOOK_URL}")

async def shutdown():
    await application.stop()
    await application.shutdown()

# Starlette app setup
routes = [
    Route(f"/{TOKEN}", webhook, methods=["POST"]),
    Route("/health", health, methods=["GET"])
]
app = Starlette(routes=routes, on_startup=[startup], on_shutdown=[shutdown])

# Run the application
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))