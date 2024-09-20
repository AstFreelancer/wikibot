import logging
from datetime import timedelta, datetime
import pytz


def get_seconds_to_midnight(timezone: str = 'Europe/Moscow') -> float:
    try:
        now = datetime.now(pytz.timezone(timezone))
        next_reset = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)  # полночь завтрашнего дня
        return (next_reset - now).total_seconds()  # спать до полуночи
    except pytz.UnknownTimeZoneError as e:
        logging.error(f"Неверное имя временной зоны: {e}")
        raise ValueError(f"Неверное имя временной зоны: {timezone}")
    except Exception as e:
        logging.error(f"Ошибка при расчете времени до полуночи: {e}")
        raise RuntimeError(f"Ошибка при расчете времени до полуночи: {e}")