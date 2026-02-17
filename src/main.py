import asyncio
import logging

from aiogram import Bot, Dispatcher

from src.config import settings
from src.bot.handlers import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


async def main() -> None:
    logger.info("Запуск бота...")
    logger.info("Администраторы: %s", settings.admin_ids)

    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()
    dp.include_router(router)

    # Удаляем вебхук если был установлен ранее
    await bot.delete_webhook(drop_pending_updates=True)

    logger.info("Бот запущен, ожидаю сообщения...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
