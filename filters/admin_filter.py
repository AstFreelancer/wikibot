import logging
from aiogram.filters import BaseFilter
from aiogram.types import Message
from config import config


class IsAdminFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        if not config or not hasattr(config, 'admin') or config.admin is None:
            logging.error("Не задано значение config.admin")
            return False

        return message.from_user.id == config.admin