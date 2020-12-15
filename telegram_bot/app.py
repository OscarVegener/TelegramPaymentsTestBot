import asyncio

from aiogram import executor

from config import admin_id
from database import create_db
from setup import bot, _


async def on_shutdown(dp):
    await bot.close()
    await dp.storage.close()
    await dp.storage.wait_closed()


async def on_startup(dp):
    await create_db()
    await bot.send_message(admin_id, _("Бот запущен!"))


if __name__ == '__main__':
    from handlers.handlers import dp
    from handlers.admin_panel import dp
    executor.start_polling(dp, on_shutdown=on_shutdown, on_startup=on_startup)
