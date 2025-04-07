import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response, HTMLResponse
from starlette.routing import Route
import asyncio
import logging
import random
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
TOKEN = os.getenv("TOKEN")  # Load from environment
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

# Webpage HTML
async def homepage(request: Request) -> HTMLResponse:
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>🔥 BIN Checker & Generator 🔥</title>
        <style>
            body {
                font-family: 'Arial', sans-serif;
                margin: 0;
                padding: 20px;
                background: linear-gradient(135deg, #1e3c72, #2a5298);
                color: #fff;
                text-align: center;
            }
            .container {
                max-width: 700px;
                margin: 0 auto;
                background: rgba(255, 255, 255, 0.1);
                padding: 20px;
                border-radius: 15px;
                box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
                backdrop-filter: blur(5px);
            }
            h1 {
                font-size: 2.5em;
                margin: 0;
                text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
            }
            h1 span { color: #ffdd57; }
            p { font-size: 1.1em; margin: 10px 0; }
            input {
                padding: 12px;
                width: 220px;
                border: none;
                border-radius: 25px;
                font-size: 1em;
                margin: 15px 0;
                box-shadow: inset 0 2px 5px rgba(0, 0, 0, 0.1);
                transition: all 0.3s ease;
            }
            input:focus {
                outline: none;
                box-shadow: 0 0 10px #ffdd57;
            }
            .button-group {
                display: flex;
                justify-content: center;
                gap: 15px;
            }
            button {
                padding: 12px 25px;
                font-size: 1em;
                border: none;
                border-radius: 25px;
                background: #ff6f61;
                color: white;
                cursor: pointer;
                transition: transform 0.2s ease, box-shadow 0.2s ease;
                box-shadow: 0 4px 10px rgba(0, 0, 0, 0.2);
            }
            button:hover {
                transform: scale(1.1);
                box-shadow: 0 6px 15px rgba(255, 111, 97, 0.5);
            }
            button:active {
                transform: scale(0.95);
            }
            pre {
                text-align: left;
                background: rgba(255, 255, 255, 0.9);
                color: #333;
                padding: 15px;
                border-radius: 10px;
                max-height: 350px;
                overflow-y: auto;
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
                margin: 20px 0;
            }
            .promo {
                margin-top: 30px;
                padding: 20px;
                background: rgba(255, 255, 255, 0.15);
                border-radius: 10px;
                box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
            }
            .promo h2 {
                font-size: 1.8em;
                color: #ffdd57;
                margin-bottom: 10px;
                text-shadow: 1px 1px 3px rgba(0, 0, 0, 0.2);
            }
            .promo p {
                font-size: 1em;
                line-height: 1.5;
            }
            .promo a {
                color: #ffdd57;
                text-decoration: none;
                font-weight: bold;
                position: relative;
                transition: all 0.3s ease;
            }
            .promo a::after {
                content: '';
                position: absolute;
                width: 0;
                height: 2px;
                bottom: -5px;
                left: 0;
                background: #ffdd57;
                transition: width 0.3s ease;
            }
            .promo a:hover::after {
                width: 100%;
            }
            .promo a:hover {
                color: #fff;
            }
            .footer {
                font-size: 0.9em;
                color: #ddd;
                margin-top: 15px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔍 BIN <span>Checker</span> & <span>Generator</span> 💳</h1>
            <p>✨ Enter a 6-digit BIN to explore its secrets or generate cards! ✨</p>
            <input type="text" id="binInput" placeholder="e.g., 424242" maxlength="6">
            <div class="button-group">
                <button onclick="checkBin()">🔎 Check BIN</button>
                <button onclick="generateCC()">🎲 Generate CC</button>
            </div>
            <pre id="output">Results will appear here... 🚀</pre>

            <div class="promo">
                <h2>🌟 Join @VengeanceSeekers 🌟</h2>
                <p>🔥 Dive into a universe of cutting-edge projects and exclusive updates at <a href="https://t.me/VengeanceSeekers" target="_blank">@VengeanceSeekers</a>. We craft innovations that spark your imagination and unveil mysteries that captivate you forever.</p>
                <p>🧠 Created by: <a href="https://t.me/Hellfirez3643" target="_blank">@Hellfirez3643</a></p>
                <p class="footer">© 2025 VengeanceSeekers. All Rights Reserved.</p>
            </div>
        </div>
        <script>
            async function fetchData(endpoint, bin) {
                const response = await fetch(endpoint, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ bin: bin })
                });
                return await response.text();
            }

            async function checkBin() {
                const bin = document.getElementById('binInput').value;
                if (!/^\d{6}$/.test(bin)) {
                    document.getElementById('output').innerText = "⚠️ Please enter a valid 6-digit BIN.";
                    return;
                }
                const result = await fetchData('/check_bin', bin);
                document.getElementById('output').innerText = result;
            }

            async function generateCC() {
                const bin = document.getElementById('binInput').value;
                if (!/^\d{6}$/.test(bin)) {
                    document.getElementById('output').innerText = "⚠️ Please enter a valid 6-digit BIN.";
                    return;
                }
                const result = await fetchData('/generate_cc', bin);
                document.getElementById('output').innerText = result;
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

# Web endpoints for BIN check and CC generation
async def check_bin_web(request: Request) -> Response:
    body = await request.json()
    bin_number = body.get("bin", "")[:6]
    if not bin_number.isdigit() or len(bin_number) < 6:
        return Response(content="Invalid BIN. Please provide a 6-digit number.", status_code=400)
    
    try:
        headers = {"X-Api-Key": API_KEY}
        response = requests.get(BIN_API_URL.format(bin_number), headers=headers, timeout=5)
        response.raise_for_status()
        data = response.json()[0]
        logger.info(f"API Response for BIN {bin_number} (web): {data}")

        brand = data.get("brand", "Unknown").capitalize()
        type_ = data.get("type", "Unknown").capitalize()
        bank = data.get("bank", "Unknown")
        country_name = data.get("country", "Unknown")
        country_code = data.get("country_code", "??").lower()
        flag = "".join([chr(0x1F1E6 + ord(c) - ord('a')) for c in country_code]) if country_code != "??" else "🌐"

        result = (
            f"BIN: {bin_number}\n"
            f"Card Brand: {brand}\n"
            f"Card Type: {type_}\n"
            f"Bank: {bank}\n"
            f"{flag} Country: {country_name}"
        )
        return Response(content=result, status_code=200)
    except Exception as e:
        return Response(content=f"Error: {str(e)}", status_code=500)

async def generate_cc_web(request: Request) -> Response:
    body = await request.json()
    bin_number = body.get("bin", "")[:6]
    if not bin_number.isdigit() or len(bin_number) < 6:
        return Response(content="Invalid BIN. Please provide a 6-digit number.", status_code=400)
    
    try:
        headers = {"X-Api-Key": API_KEY}
        response = requests.get(BIN_API_URL.format(bin_number), headers=headers, timeout=5)
        response.raise_for_status()
        data = response.json()[0]
        logger.info(f"API Response for BIN {bin_number} (web gen): {data}")

        country_name = data.get("country", "Unknown")
        country_code = data.get("country_code", "??").lower()
        flag = "".join([chr(0x1F1E6 + ord(c) - ord('a')) for c in country_code]) if country_code != "??" else "🌐"
        cc_numbers = generate_cc(bin_number, count=10)

        result = (
            f"BIN: {bin_number}\n"
            f"{flag} Country: {country_name}\n"
            f"Generated CC Numbers:\n" +
            "\n".join([f"{cc}" for cc in cc_numbers])
        )
        return Response(content=result, status_code=200)
    except Exception as e:
        return Response(content=f"Error: {str(e)}", status_code=500)

# Telegram bot handlers
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
            f"```\n"
        )
        await update.message.reply_text(message, parse_mode="MarkdownV2")
    except requests.Timeout:
        await update.message.reply_text("⏳ Request timed out. Please try again later.")
    except requests.RequestException as e:
        if response.status_code == 429:
            await update.message.reply_text("⏱️ Rate limit reached. Please try again later.")
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
        cc_numbers = generate_cc(bin_number, count=10)

        message = (
            f"```\n"
            f"📒 *BIN*: {escape_md(bin_number)}\n"
            f"{flag} *Country*: {country_name}\n"
            f"💳 *Generated CC Numbers*:\n" +
            "\n".join([f"  • {escape_md(cc)}" for cc in cc_numbers]) + "\n"
            f"✅ *Bot by*: @Hellfirez3643\n"
            f"```\n"
        )
        await update.message.reply_text(message, parse_mode="MarkdownV2")
    except requests.Timeout:
        await update.message.reply_text("⏳ Request timed out. Please try again later.")
    except requests.RequestException as e:
        if response.status_code == 429:
            await update.message.reply_text("⏱️ Rate limit reached. Please try again later.")
        else:
            await update.message.reply_text(f"❌ Error generating CC: {str(e)}")
    except (ValueError, IndexError):
        await update.message.reply_text("❌ Invalid response from BIN API or BIN not found.")
    except Exception as e:
        await update.message.reply_text(f"❌ Unexpected error: {str(e)}")

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

# Starlette app setup with routes
routes = [
    Route("/", homepage, methods=["GET"]),
    Route("/check_bin", check_bin_web, methods=["POST"]),
    Route("/generate_cc", generate_cc_web, methods=["POST"]),
    Route(f"/{TOKEN}", webhook, methods=["POST"]),
    Route("/health", health, methods=["GET"])
]
app = Starlette(routes=routes, on_startup=[startup], on_shutdown=[shutdown])

# Run the application
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))