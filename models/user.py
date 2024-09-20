from typing import NamedTuple


class User(NamedTuple):
    user_id: int
    telegram_id: int
    is_admin: bool
    daily_requests: int
    total_requests: int
