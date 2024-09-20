import logging
from typing import Any, Dict, Awaitable, Callable
from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject, User, CallbackQuery, InlineQuery, Update
from cachetools import TTLCache
from database.db import Database


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, cache_limit: TTLCache):
        super().__init__()
        self.cache_limit = cache_limit

    async def __call__(self, handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]], event: TelegramObject,
                       data: Dict[str, Any]) -> Any:
        try:
            user: User = data.get('event_from_user')
            if user is not None:
                if self.cache_limit and user.id in self.cache_limit:
                    await self._send_limit_exceeded_message(event)
                    return  # не пропускать апдейт в следующий роутер

                # Проверка лимитов в базе данных, если пользователя нет в кэше
                db: Database = data.get('db')
                if db is None:
                    raise ValueError("Не задана БД")

                if not await db.check_limits(user.id):
                    self.cache_limit[user.id] = True  # лимит исчерпан
                    await self._send_limit_exceeded_message(event)
                    return  # не пропускать апдейт в следующий роутер

            return await handler(event, data)
        except Exception as e:
            logging.error(f"Ошибка при проверке лимитов пользователя: {e}")
            return await handler(event, data)

    async def _send_limit_exceeded_message(self, event: TelegramObject):
        text = "Вы исчерпали лимит запросов на сегодня."

        if isinstance(event, Message):
            await event.answer(text)
        elif isinstance(event, CallbackQuery):
            await event.answer(text, show_alert=True)
        elif isinstance(event, InlineQuery):
            # Можно вернуть пустой ответ inline query
            await event.answer([], switch_pm_text=text, switch_pm_parameter="start")
        elif isinstance(event, Update):
            # Если event это Update, постараемся извлечь его составляющие
            if event.message:
                await event.message.answer(text)
            elif event.callback_query:
                await event.callback_query.answer(text, show_alert=True)
            elif event.inline_query:
                await event.inline_query.answer([], switch_pm_text=text, switch_pm_parameter="start")
            else:
                logging.warning(f"Пользователь исчерпал лимит, но ни один из подтипов события не определен: {event}")
        else:
            logging.warning(
                f"Пользователь исчерпал лимит, но мы не смогли ему это ответить для события: {type(event)}")