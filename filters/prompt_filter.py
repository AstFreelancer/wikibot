import logging

from aiogram.filters import BaseFilter
from aiogram.types import Message

from config import config


class GoodPromptFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        if (not config or not hasattr(config, 'min_prompt_len') or config.min_prompt_len is None
                or not hasattr(config, 'max_prompt_len') or config.max_prompt_len is None
                or not hasattr(config, 'command_list') or config.command_list is None):
            logging.error("Не задано значение min/max_prompt_len/command_list")
            return True  # не имеем формального права придраться

        return (config.min_prompt_len <= len(message.text) <= config.max_prompt_len and
                message.text not in config.command_list)


class CommandFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        if not config or not hasattr(config, 'command_list') or config.command_list is None:
            logging.error("Не задано значение min/max_prompt_len/command_list")
            return True  # техническая победа
        return message.text in config.command_list
