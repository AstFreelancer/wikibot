import asyncio
import logging
from datetime import date, datetime
from typing import Optional, List, Any
import asyncpg

from models.prompt import Prompt
from models.user import User


class SingletonMeta(type):  # метаклассы управляют поведением классов, а не экземпляров
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]


# Инициализация базы данных
def ensure_pool(func):  # декоратор для автоматической проверки инициализации пула соединений
    async def wrapper(self, *args, **kwargs):
        if self.pool is None:
            logging.error(f"Ошибка: Пул соединений не был инициализирован")
            return
        return await func(self, *args, **kwargs)

    return wrapper


class Database(metaclass=SingletonMeta):
    def __init__(self, database_url, acquire_timeout: int = 10):
        self.database_url = database_url
        self.pool: Optional[asyncpg.pool.Pool] = None
        self._pool_lock = asyncio.Lock()  # Добавляем блокировку для предотвращения гонок
        self.acquire_timeout = acquire_timeout

    async def create_pool(self):
        async with self._pool_lock:  # Используем блокировку для предотвращения параллельных вызовов
            if self.pool is None:
                try:
                    self.pool = await asyncpg.create_pool(dsn=self.database_url)
                    logging.info("Соединение с базой данных установлено")
                except (asyncpg.PostgresError, Exception) as e:
                    logging.error(f"Ошибка при установлении соединения с базой данных: {e}")
                    raise

    async def close_pool(self):
        async with self._pool_lock:  # Используем блокировку для предотвращения параллельных вызовов
            if self.pool is not None:
                try:
                    logging.info("Пытаемся закрыть пул соединений")
                    await self.pool.close()
                    self.pool = None
                    logging.info("Соединение с базой данных закрыто")
                except (asyncpg.PostgresError, Exception) as e:
                    logging.error(f"Ошибка при закрытии соединения с базой данных: {e}")
                    raise

    async def execute(self, query: str, *args: Any) -> Any:
        try:
            async with self.pool.acquire(timeout=self.acquire_timeout) as connection:  # аренда соединения из пула, как каршеринг
                result = await connection.execute(query, *args)
                return result
        except asyncpg.PostgresError as e:
            logging.error(f"Ошибка выполнения запроса: {e}")
            raise
        except asyncio.TimeoutError as e:
            logging.error(f"Таймаут при аренде соединения: {e}")
            raise
        except Exception as e:
            logging.error(f"Неизвестная ошибка при выполнении запроса: {e}")
            raise

    @ensure_pool
    async def fetchrow(self, query: str, *args: Any) -> Optional[asyncpg.Record]:
        try:
            async with self.pool.acquire(timeout=self.acquire_timeout) as connection:
                result = await connection.fetchrow(query, *args)
                return result
        except asyncpg.PostgresError as e:
            logging.error(f"Ошибка выполнения запроса: {e}")
            raise
        except asyncio.TimeoutError as e:
            logging.error(f"Таймаут при аренде соединения: {e}")
            raise
        except Exception as e:
            logging.error(f"Неизвестная ошибка при выполнении запроса: {e}")
            raise

    @ensure_pool
    async def fetch(self, query: str, *args: Any) -> List[asyncpg.Record]:
        try:
            async with self.pool.acquire(timeout=self.acquire_timeout) as connection:
                result = await connection.fetch(query, *args)
                return result
        except asyncpg.PostgresError as e:
            logging.error(f"Ошибка выполнения запроса: {e}")
            raise
        except asyncio.TimeoutError as e:
            logging.error(f"Таймаут при аренде соединения: {e}")
            raise
        except Exception as e:
            logging.error(f"Неизвестная ошибка при выполнении запроса: {e}")
            raise

    @ensure_pool
    async def init_db(self):
        try:
            logging.info("Запуск инициализации базы данных")
            # тройные кавычки для многострочных запросов
            await self.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id SERIAL PRIMARY KEY,
                    telegram_id BIGINT UNIQUE NOT NULL,
                    is_admin BOOLEAN NOT NULL DEFAULT FALSE,
                    daily_requests INTEGER NOT NULL DEFAULT 0,
                    total_requests INTEGER NOT NULL DEFAULT 0,
                    last_payment_date DATE DEFAULT NULL
                );
                CREATE TABLE IF NOT EXISTS prompts (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
                    prompt TEXT NOT NULL
                );
            ''')
            logging.info("Инициализация базы данных успешно завершена")
        except asyncpg.PostgresError as e:
            logging.error(f"Ошибка при инициализации базы данных: {e}")
            raise
        except Exception as e:
            logging.error(f"Неизвестная ошибка при инициализации базы данных: {e}")
            raise

    @ensure_pool
    async def add_user(self, telegram_id: int, is_admin: bool = False):
        if not isinstance(telegram_id, int):
            raise ValueError("telegram_id должен быть целым числом")
        if not isinstance(is_admin, bool):
            raise ValueError("is_admin должен быть булевым значением")
        try:
            # значения передаются как параметры запроса, поэтому в asyncpg автоматически экранируются
            result = await self.execute('''
                INSERT INTO users (telegram_id, is_admin)
                VALUES ($1, $2)
                ON CONFLICT (telegram_id) DO NOTHING
            ''', telegram_id, is_admin)

            n = await self.get_user_prompts_count(telegram_id)
            if n == 0:
                # Добавляем промпты по умолчанию
                from config import config
                for prompt in config.default_prompts:
                    await self.add_user_prompt(telegram_id, prompt)
        except asyncpg.PostgresError as e:
            logging.error(f"Ошибка при добавлении пользователя: {e}")
            raise
        except Exception as e:
            logging.error(f"Неизвестная ошибка при добавлении пользователя: {e}")
            raise

    @ensure_pool
    async def get_user(self, telegram_id: int) -> Optional[User]:
        if not isinstance(telegram_id, int):
            raise ValueError("telegram_id должен быть целым числом")

        try:
            result = await self.fetchrow('''
                SELECT user_id, telegram_id, is_admin, daily_requests, total_requests 
                FROM users 
                WHERE telegram_id=$1
            ''', telegram_id)
            if result:
                return User(**result)
            return None
        except asyncpg.PostgresError as e:
            logging.error(f"Ошибка выполнения запроса: {e}")
            raise
        except Exception as e:
            logging.error(f"Неизвестная ошибка при получении данных пользователя: {e}")
            raise

    @ensure_pool
    async def is_admin(self, telegram_id: int) -> bool | None:
        if not isinstance(telegram_id, int):
            raise ValueError("telegram_id должен быть целым числом")
        try:
            result = await self.fetchrow('''
                SELECT is_admin FROM users WHERE telegram_id=$1
                ''', telegram_id)
            if result and 'is_admin' in result:
                return result["is_admin"]
            return None

        except asyncpg.PostgresError as e:
            logging.error(f"Ошибка выполнения запроса: {e}")
            raise

        except Exception as e:
            logging.error(f"Неизвестная ошибка при проверке статуса администратора: {e}")
            raise

    @ensure_pool
    async def increment_requests(self, telegram_id: int) -> Optional[int]:
        if not isinstance(telegram_id, int):
            raise ValueError("telegram_id должен быть целым числом")
        try:
            result = await self.fetchrow('''
                UPDATE users
                SET daily_requests = daily_requests + 1,
                    total_requests = total_requests + 1
                WHERE telegram_id = $1
                RETURNING daily_requests
            ''', telegram_id)
            # Убедимся, что результат не пуст
            if result and 'daily_requests' in result:
                return result["daily_requests"]
            return None  # или какое-то значение по умолчанию
        except asyncpg.PostgresError as e:
            logging.error(f"Ошибка выполнения запроса: {e}")
            raise
        except Exception as e:
            logging.error(f"Неизвестная ошибка при обновлении запросов: {e}")
            raise

    @ensure_pool
    async def update_payment(self, telegram_id: int) -> Optional[bool]:
        if not isinstance(telegram_id, int):
            raise ValueError("telegram_id должен быть целым числом")
        try:
            today = date.today()
            result = await self.execute('''
                UPDATE users
                SET is_admin = TRUE,
                    last_payment_date = $2
                WHERE telegram_id = $1
            ''', telegram_id, today)

            # Убедимся, что результат не пуст
            if result == 0:
                logging.warning(f"Не удалось обновить дату платежа для пользователя {telegram_id}")
                return False
            return True
        except asyncpg.PostgresError as e:
            logging.error(f"Ошибка выполнения запроса: {e}")
            raise
        except Exception as e:
            logging.error(f"Неизвестная ошибка при обновлении даты платежа: {e}")
            raise

    @ensure_pool
    async def reset_daily_requests(self) -> None:
        try:
            await self.execute('UPDATE users SET daily_requests = 0')
            logging.info("Ежедневные запросы для всех пользователей успешно сброшены")
        except asyncpg.PostgresError as e:
            logging.error(f"Ошибка выполнения запроса: {e}")
            raise
        except Exception as e:
            logging.error(f"Неизвестная ошибка при сбросе ежедневных запросов: {e}")
            raise

    @ensure_pool
    async def get_top_users(self, order_by: str = 'daily_requests', limit: int = 10) -> List[User]:
        if order_by not in {'daily_requests', 'total_requests'}:
            raise ValueError(f"Invalid order_by value: {order_by}")

        if not isinstance(limit, int) or limit <= 0:
            raise ValueError("limit должно быть положительным целым числом")

        try:
            query = f"""
                SELECT user_id, telegram_id, is_admin, daily_requests, total_requests
                FROM users
                ORDER BY {order_by} DESC
                LIMIT $1
            """
            results = await self.fetch(query, limit)
            return [User(**result) for result in results] if results else []
        except asyncpg.PostgresError as e:
            logging.error(f"Ошибка выполнения запроса: {e}")
            raise
        except Exception as e:
            logging.error(f"Неизвестная ошибка при получении топ пользователей: {e}")
            raise

    @ensure_pool
    async def check_limits(self, telegram_id: int) -> bool:
        if not isinstance(telegram_id, int):
            raise ValueError("telegram_id должен быть целым числом")
        from config import config  # Lazy import to avoid circular dependency
        if not config.daily_limit_free:
            logging.warning("В настройках не установлено значение дневного лимита на запросы")
            return True

        try:
            user = await self.fetchrow('SELECT is_admin, daily_requests FROM users WHERE telegram_id=$1', telegram_id)
            if not user:
                await self.add_user(telegram_id)
                logging.warning(f"Пользователь {telegram_id} был не зарегистрирован, но мы оперативно исправили")
                user = await self.fetchrow('SELECT is_admin, daily_requests FROM users WHERE telegram_id=$1', telegram_id)

            if user and user['daily_requests'] < config.daily_limit_paid and (user['is_admin'] or user['daily_requests'] < config.daily_limit_free):
                return True
            return False
        except asyncpg.PostgresError as e:
            logging.error(f"Ошибка выполнения запроса: {e}")
            raise
        except Exception as e:
            logging.error(f"Неизвестная ошибка при проверке лимита запросов: {e}")
            raise

    @ensure_pool
    async def get_prompts_by_user(self, telegram_id: int) -> List[Prompt]:
        if not isinstance(telegram_id, int):
            raise ValueError("telegram_id должен быть целым числом")
        try:
            results = await self.fetch('''
                SELECT id, user_id, prompt
                FROM prompts
                WHERE user_id = $1
            ''', telegram_id)

            if not results:  # Проверяем, есть ли результаты
                return []

            return [Prompt(**result) for result in results]
        except asyncpg.PostgresError as e:
            logging.error(f"Ошибка выполнения запроса: {e}")
            raise
        except Exception as e:
            logging.error(f"Неизвестная ошибка при получении промптов пользователя: {e}")
            raise

    @ensure_pool
    async def get_user_prompts_count(self, telegram_id: int) -> int:
        if not isinstance(telegram_id, int):
            raise ValueError("telegram_id должен быть целым числом")
        try:
            row = await self.fetchrow('''
                SELECT COUNT(*) as count
                FROM prompts
                WHERE user_id = $1
            ''', telegram_id)

            if row and 'count' in row:  # Проверяем, наличие результата и ключа 'count'
                return row['count']
            return 0
        except asyncpg.PostgresError as e:
            logging.error(f"Ошибка выполнения запроса: {e}")
            raise
        except Exception as e:
            logging.error(f"Неизвестная ошибка при подсчете числа промптов пользователя: {e}")
            raise

    @ensure_pool
    async def get_users_count(self) -> int:
        try:
            row = await self.fetchrow('''
                SELECT COUNT(*) as count
                FROM users
            ''')

            if row and 'count' in row:  # Проверяем, наличие результата и ключа 'count'
                return row['count']
            return 0
        except asyncpg.PostgresError as e:
            logging.error(f"Ошибка выполнения запроса: {e}")
            raise
        except Exception as e:
            logging.error(f"Неизвестная ошибка при подсчете числа пользователей: {e}")
            raise

    @ensure_pool
    async def get_requests_count(self) -> int:
        try:
            row = await self.fetchrow('''
                SELECT SUM(daily_requests) as count
                FROM users
            ''')

            if row and 'count' in row:  # Проверяем, наличие результата и ключа 'count'
                return row['count']
            return 0
        except asyncpg.PostgresError as e:
            logging.error(f"Ошибка выполнения запроса: {e}")
            raise
        except Exception as e:
            logging.error(f"Неизвестная ошибка при подсчете числа запросов: {e}")
            raise

    @ensure_pool
    async def get_prompt_by_id(self, prompt_id: int) -> Optional[Prompt]:
        if not isinstance(prompt_id, int):
            raise ValueError("prompt_id должен быть целым числом")
        try:
            result = await self.fetchrow('''
                SELECT id, user_id, prompt
                FROM prompts
                WHERE id = $1
            ''', prompt_id)
            if result and 'id' in result and 'user_id' in result and 'prompt' in result:
                return Prompt(**result)  # распаковка словаря (синтаксический сахар)
            return None
        except asyncpg.PostgresError as e:
            logging.error(f"Ошибка выполнения запроса: {e}")
            raise
        except Exception as e:
            logging.error(f"Неизвестная ошибка при получении промпта по ID: {e}")
            raise

    @ensure_pool
    async def get_prompt_text_by_id(self, prompt_id: int) -> str | None:
        if not isinstance(prompt_id, int):
            raise ValueError("prompt_id должен быть целым числом")
        try:
            result = await self.fetchrow('''
                SELECT prompt
                FROM prompts
                WHERE id = $1
            ''', prompt_id)
            if result and 'prompt' in result:
                return result['prompt']  # распаковка словаря (синтаксический сахар)
            return None
        except asyncpg.PostgresError as e:
            logging.error(f"Ошибка выполнения запроса: {e}")
            raise
        except Exception as e:
            logging.error(f"Неизвестная ошибка при получении текста промпта по ID: {e}")
            raise

    @ensure_pool
    async def get_last_payment_date(self, telegram_id: int) -> Optional[datetime]:
        if not isinstance(telegram_id, int):
            raise ValueError("telegram_id должен быть целым числом")
        try:
            row = await self.fetchrow('''
                SELECT last_payment_date
                FROM users
                WHERE telegram_id = $1
            ''', telegram_id)

            # Если поле last_payment_date NULL, метод fetchrow вернёт None
            if row:
                return row['last_payment_date']  # Может быть datetime или None
            return None  # Если результат пустой (row == None)
        except asyncpg.PostgresError as e:
            logging.error(f"Ошибка выполнения запроса: {e}")
            raise
        except Exception as e:
            logging.error(f"Неизвестная ошибка при получении даты последней оплаты: {e}")
            raise

    @ensure_pool
    async def add_user_prompt(self, telegram_id: int, prompt: str) -> bool:
        if not isinstance(telegram_id, int) or not isinstance(prompt, str):
            raise ValueError("telegram_id должен быть целым числом, а prompt - строкой")

        try:
            await self.execute('''
                INSERT INTO prompts (user_id, prompt)
                VALUES ($1, $2)
            ''', telegram_id, prompt)
            return True
        except asyncpg.PostgresError as e:
            logging.error(f"Ошибка выполнения запроса на добавление промпта: {e}")
            return False

        except Exception as e:
            logging.error(f"Неизвестная ошибка при добавлении промпта: {e}")
            return False

    @ensure_pool
    async def delete_user_prompt(self, prompt_id: int) -> bool:
        if not isinstance(prompt_id, int):
            raise ValueError("prompt_id должен быть целым числом")
        try:
            result = await self.execute('''
                DELETE FROM prompts
                WHERE id = $1
            ''', prompt_id)
            if not result == 'DELETE 1':
                logging.error(f"Попытка удалить несуществующий промпт {prompt_id}")
                return False
            return True
        except asyncpg.PostgresError as e:
            logging.error(f"Ошибка выполнения запроса на удаление промпта: {e}")
            return False
        except Exception as e:
            logging.error(f"Неизвестная ошибка при удалении промпта: {e}")
            return False

    @ensure_pool
    async def edit_user_prompt(self, prompt_id: int, prompt_text: str) -> bool:
        if not isinstance(prompt_id, int) or not isinstance(prompt_text, str):
            raise ValueError("prompt_id должен быть целым числом")
        try:
            result = await self.execute('''
                UPDATE prompts
                SET prompt = $1
                WHERE id = $2
            ''', prompt_text, prompt_id)
            if not result == 'UPDATE 1':
                logging.error(f"Не удалось отредактировать промпт {prompt_id}")
                return False
            return True
        except asyncpg.PostgresError as e:
            logging.error(f"Ошибка выполнения запроса на редактирование промпта: {e}")
            return False
        except Exception as e:
            logging.error(f"Неизвестная ошибка при редактировании промпта: {e}")
            return False