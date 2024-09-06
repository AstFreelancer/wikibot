from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

like_button = InlineKeyboardButton(text="👍", callback_data='like')
dislike_button = InlineKeyboardButton(text="👎", callback_data='dislike')

keyboard = InlineKeyboardMarkup(keyboard=[[like_button, dislike_button]], resize_keyboard=True)