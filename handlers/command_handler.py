import logging

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message
import open_ai

router = Router()

@router.message(CommandStart())
async def send_welcome(message: Message):
    user_language = message.from_user.language_code
    await message.reply(f"Привет! Ваш язык интерфейса: {user_language}\n"
                        "Пришлите фото для анализа")
    # изменить значение wiki.language

@router.message(F.photo)
async def process_photo(message: Message):
    # Получение файла фото
    photo = message.photo[-1]
    # Получение информации о файле
    file_info = await message.bot.get_file(photo.file_id)
    file_path = file_info.file_path

    # Создание URL для доступа к файлу
    file_url = f'https://api.telegram.org/file/bot{message.bot.token}/{file_path}'

    # Извлечение и отправка ответа
    reply = open_ai.get_openai_response(file_url)
    await message.reply(reply)

@router.message(~F.photo)
async def process_non_photo(message: Message):
    logging.info("Получено не фото")
    await message.answer("Пришлите фото для анализа")