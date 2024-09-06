from aiogram import F, Router
from aiogram.types import CallbackQuery
import logging

router = Router()

@router.callback_query(F.data == 'like')
async def process_like(callback: CallbackQuery):
    pass

@router.callback_query(F.data == 'dislike')
async def process_dislike(callback: CallbackQuery):
    pass