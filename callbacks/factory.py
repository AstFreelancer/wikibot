from aiogram.filters.callback_data import CallbackData

class MyCallbackFactory(CallbackData, prefix='my_callback'):
    prompt_id: int
    action: str