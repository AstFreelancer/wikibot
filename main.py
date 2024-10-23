import asyncio
import logging

from loader import dp, bot
from aiogram.types import BotCommand
from cachetools import TTLCache

from database.db import Database
from handlers import command_handler, prompt_handler
from config import config

from middlewares.database_middleware import DatabaseMiddleware
from middlewares.throttling_middleware import ThrottlingMiddleware

from time_delta import get_seconds_to_midnight
from logging.handlers import TimedRotatingFileHandler

# Настройка обработчика логов с ротацией по времени
handler = TimedRotatingFileHandler(
    filename='my_log.log',
    when='midnight',         # Ротация в полночь
    interval=1,              # Частота ротации - раз в сутки
    backupCount=7,           # Сохранять последние 7 файлов логов
    encoding='utf-8'
)

# Форматирование логов
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)
logging.basicConfig(
    level=logging.DEBUG,
    handlers=[handler]
)

# список тех, кто уже превысил суточный лимит
cache_limit = TTLCache(config.max_cache_size, get_seconds_to_midnight())

# Глобальные переменные для хранения БД и задачи сброса
db: Database
reset_task: asyncio.Task

async def reset_tasks():
    global db
    while True:
        try:
            await asyncio.sleep(get_seconds_to_midnight())  # спать до полуночи
            if db is not None:
                await db.reset_daily_requests()
            cache_limit.clear()
            logging.info("Почистили кэш")
        except Exception as e:
            logging.error(f"Произошла ошибка в reset_tasks: {e}", exc_info=True)
        finally:
            # Для предотвращения бесконечного выхода из цикла при частых сбоях
            await asyncio.sleep(1)

async def startup():
    global db, reset_task
    try:
        db = Database(config.database_url)
        await db.create_pool()  # Асинхронная инициализация пула соединений
        logging.info("Создали пул")
        await db.init_db()
        logging.info("База данных успешно инициализирована")

        # Создание асинхронной задачи для сброса
        reset_task = asyncio.create_task(reset_tasks())
    except Exception as e:
        logging.error(f"Ошибка инициализации базы данных: {e}")
        raise


async def shutdown():
    global db, reset_task
    try:
        if reset_task:
            reset_task.cancel()
            try:
                await reset_task
            except asyncio.CancelledError:
                pass

        if db:
            await db.close_pool()
            logging.info("Соединение с базой данных закрыто")
    except Exception as e:
        logging.error(f"Ошибка при закрытии соединения с базой данных: {e}")
        raise

async def main():
    try:
        # Регистрируем роутеры в диспетчере
        dp.include_router(command_handler.router)
        dp.include_router(prompt_handler.router)

        await startup()

        dp.update.middleware(DatabaseMiddleware(db))
        dp.update.middleware(ThrottlingMiddleware(cache_limit))

        await bot.set_my_commands([
            BotCommand(command="/start", description="Запустить бота"),
            BotCommand(command="/help", description="Показать справку"),
            BotCommand(command="/buy", description="Купить/проверить подписку"),
            BotCommand(command="/prompts", description="Показать мои промпты"),
            BotCommand(command="/add", description="Добавить новый промпт"),
            BotCommand(command="/edit", description="Редактировать промпт"),
            BotCommand(command="/delete", description="Удалить промпт"),
            BotCommand(command="/cancel", description="Отменить команду")
        ])

        logging.info('Запускаем бота')
        await dp.start_polling(bot, skip_updates=False) #  Это спасет от проблем при обработке платежей.
    except Exception as e:
        logging.error(f"Ошибка при работе бота: {e}")
    finally:
        await shutdown()


if __name__ == '__main__':
    asyncio.run(main())
