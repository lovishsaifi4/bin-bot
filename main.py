import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Route
import asyncio

# Configuration
TOKEN = os.getenv("TOKEN", "7881163673:AAExCe9WYE4RqsKK67XauK4GG2ktfY9C6lk")
BIN_API_URL = "https://api.api-ninjas.com/v1/bin?bin={}"
API_KEY = "lQiHO34dFj8jY4xYNacj3g==oyNatSR2JdLDlWLw"
WEBHOOK_URL = os.getenv("RENDER_EXTERNAL_URL", f"https://your-service-name.onrender.com") + f"/{TOKEN}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Welcome to BIN Checker Bot! Use /bin or .bin <BIN> (e.g., /bin 123456 or .bin 412345)"
    )

async def check_bin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Please provide a BIN number. Usage: /bin <BIN>")
        return
    bin_number = context.args[0][:6]
    await process_bin(update, bin_number)

async def check_bin_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message_text = update.message.text
    if message_text.startswith(".bin"):
        bin_number = message_text.replace(".bin", "").strip()[:6]
        if not (bin_number.isdigit() and len(bin_number) >= 6):
            await update.message.reply_text("Invalid BIN. Use .bin followed by a 6-digit number.")
            return
        await process_bin(update, bin_number)

async def process_bin(update: Update, bin_number: str) -> None:
    try:
        headers = {"X-Api-Key": API_KEY}
        response = requests.get(BIN_API_URL.format(bin_number), headers=headers, timeout=5)
        response.raise_for_status()
        data = response.json()[0]

        def escape_md(text):
            chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '}', '.', '!']
            for char in chars:
                text = str(text).replace(char, f'\{char}')
            return text

        brand = escape_md(data.get("scheme", "Unknown").capitalize())
        type_ = escape_md(data.get("type", "Unknown").capitalize())
        bank = escape_md(data.get("bank", "Unknown"))
        country_name = escape_md(data.get("country", "Unknown"))
        country_code = data.get("country_code", "??").lower()

        flag = "".join([chr(0x1F1E6 + ord(c) - ord('a')) for c in country_code]) if country_code != "??" else "🌐"

        message = (
            f"```\n"
            f"📒 BIN: {bin_number}\n"
            f"🏷️ Card Brand: {brand}\n"
            f"💳 Card Type: {type_}\n"
            f"🏦 Bank: {bank}\n"
            f"{flag} Country: {country_name}\n"
            f"✅ Bot by @Hellfirez3643\n"
            f"```"
        )
        await update.message.reply_text(message, parse_mode="MarkdownV2")
    except requests.Timeout:
        await update.message.reply_text("Request timed out. Please try again later.")
    except requests.RequestException as e:
        if response.status_code == 429:
            await update.message.reply_text("Rate limit reached. Please wait and try again later.")
        else:
            await update.message.reply_text(f"Error checking BIN: {str(e)}")
    except (ValueError, IndexError):
        await update.message.reply_text("Invalid response from BIN API or BIN not found.")
    except Exception as e:
        await update.message.reply_text(f"Unexpected error: {str(e)}")

# Webhook handler
async def webhook(request: Request) -> Response:
    update = Update.de_json(await request.json(), application.bot)
    if update:
        await application.process_update(update)
    return Response(status_code=200)

# Health check endpoint
async def health(request: Request) -> Response:
    return Response(content="OK", status_code=200)

# Starlette app for webhook
routes = [
    Route(f"/{TOKEN}", webhook, methods=["POST"]),
    Route("/health", health, methods=["GET"])
]
app = Starlette(routes=routes)

# Application setup
application = Application.builder().token(TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("bin", check_bin_command))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_bin_message))

# Set webhook on startup
async def set_webhook():
    await application.bot.set_webhook(url=WEBHOOK_URL)
    print(f"Webhook set to {WEBHOOK_URL}")

# Run the application
if __name__ == "__main__":
    import uvicorn
    # Run the webhook setup as a one-time task
    asyncio.run(set_webhook())
    # Start the Starlette app
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))