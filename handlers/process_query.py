import logging

from aiogram.exceptions import TelegramAPIError
from aiogram.types import Message

import open_ai
from database.db import Database


async def process_query(message: Message, db: Database, query: str):  # нет проверок, т.к. мы их делаем в мидлвари
    user_id = message.from_user.id
    try:
        reply = open_ai.get_openai_response(None, query)
        if not reply:
            raise ValueError("Некорректный ответ от OpenAI.")
    except Exception as e:
        logging.error(f"Ошибка при получении ответа от OpenAI: {e}")
        await message.reply("Произошла ошибка при обработке запроса. Попробуйте позже.")
        return

    try:
        await message.reply(reply)
    except TelegramAPIError as e:
        logging.error(f"Ошибка при отправке сообщения пользователю: {e}")
        await message.answer("Произошла ошибка при отправке сообщения. Попробуйте позже.")
        return

    try:
        daily_requests = await db.increment_requests(user_id)
        if daily_requests is None:
            raise ValueError("Не удалось обновить количество запросов в базе данных.")
        if isinstance(daily_requests, int):
            await message.answer(f"Всего запросов от вас за сегодня: {daily_requests}")
    except Exception as e:
        logging.error(f"Ошибка при обновлении в БД количества запросов от пользователя {user_id}: {e}")
        await message.answer("Произошла непредвиденная ошибка. Попробуйте позже.")

async def process_photo(message: Message, db: Database, prompt_text: str | None):
    try:
        if message.caption and isinstance(message.caption, str):
            # Добавляем текст сообщения к prompt_text
            prompt_text = f"{prompt_text} \n {message.caption}" if prompt_text else message.caption

        if not message.photo:
            raise ValueError("Сообщение не содержит фото.")
        photo = message.photo[-1]
        # Получение информации о файле
        file_info = await message.bot.get_file(photo.file_id)
        if not file_info:
            raise ValueError("Получена неверная информация о файле {photo.file_id}")
        file_path = file_info.file_path
        if not file_path:
            raise ValueError(f"Ошибка получения пути к файлу {photo.file_id}")
        if not message.bot.token:
            raise ValueError("Ошибка получения токена бота")
        file_url = f'https://api.telegram.org/file/bot{message.bot.token}/{file_path}'
    except Exception as e:
        logging.error(f"Ошибка при получении информации о файле: {e}")
        await message.reply("Произошла ошибка при получении информации о файле. Попробуйте снова.")
        return

    try:
        reply = open_ai.get_openai_response(file_url, prompt_text)
        if not reply:
            raise ValueError("Некорректный ответ от OpenAI.")
    except Exception as e:
        logging.error(f"Ошибка при получении ответа от OpenAI: {e}")
        await message.reply("Произошла ошибка при обработке запроса. Попробуйте снова.")
        return

    try:
        await message.reply(reply)
        user_id = message.from_user.id
        daily_requests = await db.increment_requests(user_id)
        if daily_requests is None:
            raise ValueError("Не удалось обновить количество запросов в базе данных.")
        if isinstance(daily_requests, int):
            await message.answer(f"Всего запросов от вас за сегодня: {daily_requests}")
    except Exception as e:
        logging.error(f"Ошибка при отправке ответа и информации о запросах пользователю: {e}")
        await message.answer("Произошла ошибка при отправке ответа. Попробуйте позже.")