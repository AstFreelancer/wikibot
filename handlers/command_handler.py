import logging
from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from database.db import Database

router = Router()


@router.message(Command(commands=['cancel']))
async def cancel(message: Message, state: FSMContext):
    try:
        await message.reply("Команда отменена")

        # Проверка состояния и его очистка
        current_state = await state.get_state()
        if current_state is not None:
            await state.clear()
    except Exception as e:
        # Логирование ошибок
        logging.error(f"Ошибка при обработке команды /cancel: {e}")
        await message.reply("Произошла ошибка при обработке команды.")


@router.message(Command(commands=['start']))
async def send_welcome(message: Message, db: Database):
    try:
        #    user_language = message.from_user.language_code
        user_id = message.from_user.id
        await db.add_user(user_id)
        logging.info(f"Зарегистрирован пользователь {user_id}, если его не было в БД")
        await message.reply(f"Привет! Пришлите запрос или выберите промпт.\n")
    except Exception as e:
        # Логирование ошибок
        logging.error(f"Ошибка при выполнении команды /start: {e}")
        await message.reply("Произошла ошибка при обработке команды.")


@router.message(Command(commands=['help']))
async def send_help(message: Message):
    try:
        await message.reply(f"Команды:\n"
                            "/prompts - показать мои промпты\n"
                            "/add - добавить новый промпт\n"
                            "/edit - редактировать промпт\n"
                            "/delete - удалить промпт")
    except Exception as e:
        # Логирование ошибок
        logging.error(f"Ошибка при выполнении команды /help: {e}")
        await message.reply("Произошла ошибка при обработке команды.")




