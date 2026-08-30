import asyncio
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup
from .config import settings
from .db import init_db

dp = Dispatcher()

@dp.message(Command("start"))
async def start(message: Message):
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⚙️ Settings"), KeyboardButton(text="📍 Nearby")],
            [KeyboardButton(text="🔋 Charging status"), KeyboardButton(text="👀 Watch")]
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
    await message.answer(
        "Settings MVP:\n"
        "• Supported connectors: CHAdeMO / Type 1 / GB-T DC / GB-T AC / CCS / Type 2\n"
        "• Default radius: 2 km\n"
        "• Providers: Malanka / Evika\n\n"
        "The persistent settings store is the next provider-specific integration step."
    )

@dp.message(Command("nearby"))
async def nearby(message: Message):
    await message.answer("Please send your Telegram location. I will search compatible stations in the configured radius.")

@dp.message(Command("status"))
async def status(message: Message):
    await message.answer("Charging-session monitoring is ready for authenticated provider adapters.")

async def main():
    await init_db()
    bot = Bot(settings.telegram_bot_token)
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
