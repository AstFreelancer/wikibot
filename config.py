from environs import Env
from dataclasses import dataclass


@dataclass
class Config:
    __instance = None
    def __new__(cls):
        if cls.__instance is None:
            env: Env = Env()
            env.read_env()
            cls.__instance = super(Config, cls).__new__(cls)
            cls.__instance.bot_token = env('BOT_TOKEN')
            cls.__instance.openai_key = env('OPENAI_KEY')
            cls.__instance.plant_prompt = env('PLANT_PROMPT')
            cls.__instance.allowed_extensions = env('ALLOWED_EXTENSIONS')
            cls.__instance.max_file_size = env('MAX_FILE_SIZE')
        return cls.__instance

