import asyncio
import logging

from aiogram import Bot, Dispatcher

from db import init_db
from auth import router as auth_router
from admin import router as admin_router
from mentor import router as mentor_router
from warehouse import router as warehouse_router


logging.basicConfig(level=logging.INFO)

BOT_TOKEN = "8632022187:AAEW0sJjcPlytKtpclHehc2_r4ATBOVxoRY"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


async def main():
    try:
        init_db()

        # ✅ СНАЧАЛА подключаем роутеры
        dp.include_router(auth_router)
        dp.include_router(admin_router)
        dp.include_router(mentor_router)
        dp.include_router(warehouse_router)

        # ✅ ПОТОМ запускаем бота
        await dp.start_polling(bot)

    except Exception as e:
        print("ОШИБКА:", e)


if __name__ == "__main__":
    asyncio.run(main())