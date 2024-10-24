import json
import logging

from environs import Env, EnvError
from dataclasses import dataclass


@dataclass
class Config:
    __instance = None

    def __new__(cls):
        try:
            if cls.__instance is None:
                env: Env = Env()
                env.read_env()
                cls.__instance = super(Config, cls).__new__(cls)
                cls.__instance.bot_token = env('BOT_TOKEN')
                cls.__instance.openai_key = env('OPENAI_KEY')
                cls.__instance.min_prompt_len = env.int('MIN_PROMPT_LEN', default=5)
                cls.__instance.max_prompt_len = env.int('MAX_PROMPT_LEN', default=1000)
                cls.__instance.max_query_len = env.int('MAX_QUERY_LEN', default=1000)
                cls.__instance.command_list = [f"/{cmd.strip()}" for cmd in env('COMMAND_LIST').split(',')]
                cls.__instance.daily_limit_free = env.int('DAILY_LIMIT_FREE', default=10)
                cls.__instance.daily_limit_paid = env.int('DAILY_LIMIT_PAID', default=50)
                cls.__instance.database_url = env('DATABASE_URL')
                cls.__instance.max_cache_size = env.int('MAX_CACHE_SIZE', default=10000)
                cls.__instance.ttl = env.int('TTL', default=86400)
                cls.__instance.default_prompts = [f"{p.strip()}" for p in env('DEFAULT_PROMPTS').split(';')]
                cls.__instance.admin = env.int('ADMIN', default=683708227)
                cls.__instance.max_prompts_per_user = env.int('MAX_PROMPTS_PER_USER', default=10)
                cls.__instance.provider_token = env('PROVIDER_TOKEN')
                cls.__instance.currency = env('CURRENCY')
                cls.__instance.price = env.int('PRICE')
                provider_data = {
                    "provider_data": {
                        "receipt": {
                            "items": [
                                {
                                    "description": "Подписка на месяц",
                                    "quantity": "1.00",
                                    "amount": {
                                        "value": f"{cls.__instance.price / 100:.2f}",
                                        "currency": cls.__instance.currency
                                    },
                                    "vat_code": 1
                                }
                            ]
                        }
                    }
                }
                cls.__instance.provider_data = json.dumps(provider_data)
            return cls.__instance
        except EnvError as e:
            logging.error(f"Ошибка чтения переменных окружения: {e}")
            raise RuntimeError(f"Ошибка чтения переменных окружения: {e}")
        except Exception as e:
            logging.error(f"Произошла непредвиденная ошибка: {e}")


config = Config()
