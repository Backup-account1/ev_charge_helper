import asyncio
import logging
import sys
from pathlib import Path
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from .config import settings
from .db import init_db

# Configure logging
Path("logs").mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/ev_charge_helper.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

dp = Dispatcher()

@dp.message(Command("start"))
async def start(message: Message):
    logger.info(f"User {message.from_user.id} started the bot")
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="\u2699\ufe0f Settings"), KeyboardButton(text="\ud83d\udccd Nearby")],
            [KeyboardButton(text="\ud83d\udd0b Charging status"), KeyboardButton(text="\ud83d\udc40 Watch")]
        ],
        resize_keyboard=True
    )
    await message.answer(
        "EV Charge Agent\n\n"
        "Let's configure your car, connectors and provider preferences.",
        reply_markup=kb
    )

@dp.message(Command("settings"))
async def settings_cmd(message: Message):
    logger.info(f"User {message.from_user.id} requested settings")
    await message.answer(
        "Settings MVP:\n"
        "\u2022 Supported connectors: CHAdeMO / Type 1 / GB-T DC / GB-T AC / CCS / Type 2\n"
        "\u2022 Default radius: 2 km\n"
        "\u2022 Providers: Malanka / Evika\n\n"
        "The persistent settings store is the next provider-specific integration step."
    )

@dp.message(Command("nearby"))
async def nearby(message: Message):
    logger.info(f"User {message.from_user.id} requested nearby stations")
    await message.answer("Please send your Telegram location. I will search compatible stations in the configured radius.")

@dp.message(Command("status"))
async def status(message: Message):
    logger.info(f"User {message.from_user.id} requested status")
    await message.answer("Charging-session monitoring is ready for authenticated provider adapters.")

@dp.message(Command("watch"))
async def watch_cmd(message: Message):
    logger.info(f"User {message.from_user.id} requested watch")
    await message.answer(
        "👀 Watch mode\n\n"
        "Monitoring will check your active charging session periodically.\n\n"
        "⚠️ Provider monitoring is not connected yet."
    )


@dp.message(lambda message: message.text == "👀 Watch")
async def watch_button(message: Message):
    await watch_cmd(message)
async def main():
    logger.info("Starting EV Charge Agent bot")
    
    # Validate token
    if not settings.telegram_bot_token or settings.telegram_bot_token.strip() == "":
        logger.error("TELEGRAM_BOT_TOKEN is not set in .env file. Please add your Telegram bot token.")
        logger.error("Create a .env file with: TELEGRAM_BOT_TOKEN=your_token_here")
        sys.exit(1)
    
    # Initialize database
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        sys.exit(1)
    
    # Start bot
    try:
        bot = Bot(settings.telegram_bot_token)
        logger.info("Bot instance created, starting polling...")
        await dp.start_polling(bot)
    except TelegramForbiddenError as e:
        logger.error(f"Telegram Forbidden Error: {e}")
        sys.exit(1)
    except TelegramBadRequest as e:
        logger.error(f"Telegram Bad Request: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)
    finally:
        logger.info("Shutting down bot")
        if 'bot' in locals():
            await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        sys.exit(0)
