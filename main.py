import asyncio
import logging
from wiki import Wiki
from aiogram import Bot, Dispatcher
from handlers import keyboard_handler, command_handler
from config import Config

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')  # , filename='my_log.log')

config = Config()


# wiki = Wiki("ru")
# wiki_result = wiki.get_wiki("щетинник", "Plantae")
# print(wiki_result)

async def main():
    bot = Bot(token=config.bot_token)
    dp = Dispatcher()

    # Регистриуем роутеры в диспетчере
    dp.include_router(keyboard_handler.router)
    dp.include_router(command_handler.router)

    await dp.start_polling(bot, skip_updates=True)
    logging.info('Starting bot')

if __name__ == '__main__':
    asyncio.run(main())