import logging

from aiogram import Router, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import config

from FSM import FSMPrompt
from callbacks.factory import MyCallbackFactory
from filters.admin_filter import IsAdminFilter

from filters.prompt_filter import GoodPromptFilter, CommandFilter
from handlers.process_query import *

router = Router()


@router.message(Command(commands=['prompts']))
async def list_prompts(message: Message, db: Database, state: FSMContext):
    try:
        # Проверка состояния и его очистка
        current_state = await state.get_state()
        if current_state is not None:
            await state.clear()  # чтобы свободно перейти сюда из любого другого состояния
        user_id = message.from_user.id
        prompts = await db.get_prompts_by_user(user_id)
        if prompts is None:
            raise ValueError("Ошибка при получении промптов из базы данных.")

        if prompts:
            keyboard = InlineKeyboardBuilder()
            for prompt in prompts:
                if not hasattr(prompt, 'id') or not hasattr(prompt, 'prompt'):
                    raise AttributeError(f"У промпта отсутствуют необходимые атрибуты: {prompt}")
                cb_data = MyCallbackFactory(action="use", prompt_id=prompt.id)
                keyboard.button(text=prompt.prompt, callback_data=cb_data.pack())
            keyboard.adjust(1)
            await message.reply("Вот ваши промпты:", reply_markup=keyboard.as_markup())
        else:
            await message.reply("У вас нет ни одного промпта. Создайте их с помощью команды /add.")
    except AttributeError as e:
        logging.error(f"Ошибка атрибута: {e}")
        await message.reply("Произошла ошибка при обработке атрибутов. Попробуйте позже.")

    except ValueError as e:
        logging.error(f"Ошибка значения: {e}")
        await message.reply("Произошла ошибка при получении данных. Попробуйте позже.")

    except TypeError as e:
        logging.error(f"Ошибка типа данных: {e}")
        await message.reply("Произошла ошибка типа данных. Попробуйте позже.")

    except TelegramAPIError as e:
        logging.error(f"Ошибка Telegram API: {e}")
        await message.reply("Произошла ошибка при взаимодействии с Telegram. Попробуйте позже.")

    except Exception as e:
        logging.error(f"Произошла непредвиденная ошибка: {e}")
        await message.reply("Произошла непредвиденная ошибка. Попробуйте позже.")


@router.message(Command(commands=['add']))
async def add_prompt(message: Message, db: Database, state: FSMContext):
    try:
        # Проверка состояния и его очистка
        current_state = await state.get_state()
        if current_state is not None:
            await state.clear()  # чтобы свободно перейти сюда из любого другого состояния

        user_id = message.from_user.id

        try:
            current_prompts_count = await db.get_user_prompts_count(user_id)
            if current_prompts_count is None:
                raise ValueError("Ошибка при получении количества промптов из базы данных.")
        except Exception as e:
            logging.error(f"Ошибка при получении количества промптов из базы данных: {e}")
            await message.reply("Произошла ошибка при получении данных. Попробуйте позже.")
            return

        if config.max_prompts_per_user:
            if current_prompts_count >= config.max_prompts_per_user:
                await message.reply(
                    f"У вас уже имеется {current_prompts_count} промптов. Вы не можете добавить новый промпт.")
                return

        try:
            if config.min_prompt_len and config.max_prompt_len:
                await message.reply(
                    f"Введите новый промпт длиной от {config.min_prompt_len} до {config.max_prompt_len} символов или отмените добавление командой /cancel")
            else:
                await message.reply(
                    f"Введите новый промпт или отмените добавление командой /cancel")
            await state.set_state(FSMPrompt.adding)
        except TelegramAPIError as e:
            logging.error(f"Ошибка при отправке сообщения пользователю: {e}")
            await message.reply("Произошла ошибка при отправке сообщения. Попробуйте позже.")

    except TypeError as e:
        logging.error(f"Ошибка типа данных: {e}")
        await message.reply("Произошла ошибка типа данных. Попробуйте позже.")

    except ValueError as e:
        logging.error(f"Ошибка значения: {e}")
        await message.reply("Произошла ошибка при обработке данных. Попробуйте позже.")

    except TelegramAPIError as e:
        logging.error(f"Ошибка Telegram API: {e}")
        await message.reply("Произошла ошибка при взаимодействии с Telegram. Попробуйте позже.")

    except Exception as e:
        logging.error(f"Произошла непредвиденная ошибка: {e}")
        await message.reply("Произошла непредвиденная ошибка. Попробуйте позже.")


# ловим промпт в правильном формате
@router.message(StateFilter(FSMPrompt.adding), GoodPromptFilter())
async def get_new_prompt(message: types.Message, db: Database, state: FSMContext):
    try:
        user_id = message.from_user.id
        if not message.text:
            raise ValueError("Отсутствует текст сообщения")
        prompt = message.text
        if await db.add_user_prompt(user_id, prompt):
            await message.answer("Новый промпт добавлен.")
        else:
            await message.answer("Не удалось добавить промпт. Попробуйте позже.")

        current_state = await state.get_state()
        if current_state is not None:
            await state.clear()  # чтобы свободно перейти сюда из любого другого состояния

    except Exception as e:
        logging.error(f"Ошибка при добавлении промпта в базу данных: {e}")
        await message.reply("Произошла ошибка при добавлении вашего промпта. Попробуйте позже.")


# и в неправильном
@router.message(StateFilter(FSMPrompt.adding), ~CommandFilter())  # если это не команда
# любая команда имеет наивысший приоритет и отменяет все действо
async def get_new_prompt(message: types.Message):
    try:
        await message.answer("Недопустимый промпт! Пришлите новый вариант или отмените добавление командой /cancel")
    except Exception as e:
        logging.error(f"Ошибка при обработке недопустимого промпта: {e}")
        await message.reply("Произошла ошибка при добавлении вашего промпта. Попробуйте позже.")


@router.message(Command(commands=['delete']))
async def delete_prompt(message: Message, db: Database, state: FSMContext):
    try:
        # Проверка состояния и его очистка
        current_state = await state.get_state()
        if current_state is not None:
            await state.clear()  # чтобы свободно перейти сюда из любого другого состояния, т.е. приоритет любой команды /... выше, чем все предыдущее
        user_id = message.from_user.id

        # Получение промптов пользователя из базы данных
        try:
            prompts = await db.get_prompts_by_user(user_id)
            if prompts is None:
                raise ValueError("Ошибка при получении промптов из базы данных.")
        except Exception as e:
            logging.error(f"Ошибка при получении промптов из базы данных для пользователя {user_id}: {e}")
            await message.reply("Произошла ошибка при получении данных. Попробуйте позже.")
            return

        if prompts:
            keyboard = InlineKeyboardBuilder()
            for prompt in prompts:
                if not hasattr(prompt, 'id') or not hasattr(prompt, 'prompt'):
                    raise AttributeError(f"У промпта отсутствуют необходимые атрибуты: {prompt}")
                cb_data = MyCallbackFactory(action="delete", prompt_id=prompt.id)
                keyboard.button(text="❌ " + prompt.prompt, callback_data=cb_data.pack())
            keyboard.adjust(1)
            await message.reply("Выберите промпт для удаления или отмените операцию командой /cancel",
                                reply_markup=keyboard.as_markup())
        else:
            await message.reply("У вас нет промптов для удаления.")
    except Exception as e:
        logging.error(f"Ошибка при выводе списка промптов для удаления: {e}")
        await message.reply("Произошла ошибка при обработке данных. Попробуйте позже.")


@router.message(Command(commands=['edit']))
async def edit_prompt(message: Message, db: Database, state: FSMContext):
    try:
        # Проверка состояния и его очистка
        current_state = await state.get_state()
        if current_state is not None:
            await state.clear()  # чтобы свободно перейти сюда из любого другого состояния

        user_id = message.from_user.id
        # Получение промптов пользователя из базы данных
        try:
            prompts = await db.get_prompts_by_user(user_id)
            if prompts is None:
                raise ValueError("Ошибка при получении промптов из базы данных.")
        except Exception as e:
            logging.error(f"Ошибка при получении промптов из базы данных для пользователя {user_id}: {e}")
            await message.reply("Произошла ошибка при получении данных. Попробуйте позже.")
            return

        if prompts:
            keyboard = InlineKeyboardBuilder()
            for prompt in prompts:
                if not hasattr(prompt, 'id') or not hasattr(prompt, 'prompt'):
                    raise AttributeError(f"У промпта отсутствуют необходимые атрибуты: {prompt}")
                cb_data = MyCallbackFactory(action="edit", prompt_id=prompt.id)
                keyboard.button(text="✏️ " + prompt.prompt, callback_data=cb_data.pack())
            keyboard.adjust(1)
            await message.reply("Выберите промпт для редактирования или отмените операцию командой /cancel",
                                reply_markup=keyboard.as_markup())
        else:
            await message.reply("У вас нет промптов для редактирования.")
    except Exception as e:
        logging.error(f"Ошибка при выводе списка промптов для редактирования: {e}")
        await message.reply("Произошла ошибка при обработке данных. Попробуйте позже.")


@router.callback_query(MyCallbackFactory.filter(F.action == 'edit'))
async def edit_prompt(callback_query: types.CallbackQuery, callback_data: MyCallbackFactory, db: Database,
                      state: FSMContext):
    try:
        # Проверка наличия и типа prompt_id
        if not callback_data or not hasattr(callback_data, 'prompt_id') or not isinstance(callback_data.prompt_id, int):
            raise TypeError("Не удалось получить prompt_id из callback_data.")

        prompt_id = callback_data.prompt_id

        # Получение промпта по id из базы данных
        try:
            prompt = await db.get_prompt_by_id(prompt_id)
            if prompt is None:
                raise ValueError("Ошибка при получении промпта из базы данных.")
        except Exception as e:
            logging.error(f"Ошибка при получении промпта по id {prompt_id}: {e}")
            await callback_query.message.reply("Произошла ошибка при получении данных. Попробуйте позже.")
            await callback_query.answer()  # Закрываем уведомление
            return

        # Проверка наличия необходимых атрибутов у промпта
        if not hasattr(prompt, 'id') or not hasattr(prompt, 'prompt'):
            raise AttributeError(f"У промпта отсутствуют необходимые атрибуты: {prompt}")

        await state.update_data(prompt_id=prompt.id)

        if config and config.min_prompt_len and config.max_prompt_len:
            await callback_query.message.reply(
                f"Вы редактируете промпт:\n"
                f"{prompt.prompt}\n"
                f"Введите новое значение промпта длиной от {config.min_prompt_len} до {config.max_prompt_len} символов или отмените редактирование командой /cancel")
        else:
            await callback_query.message.reply(
                f"Вы редактируете промпт:\n"
                f"{prompt.prompt}\n"
                f"Введите новое значение промпта или отмените редактирование командой /cancel")

        await state.set_state(FSMPrompt.editing)
        await callback_query.answer()  # пусто, чтобы не мигала кнопка

    except TypeError as e:
        logging.error(f"Ошибка типа данных: {e}")
        await callback_query.message.reply("Произошла ошибка типа данных. Попробуйте позже.")
        await callback_query.answer()  # Закрываем уведомление

    except ValueError as e:
        logging.error(f"Ошибка значения: {e}")
        await callback_query.message.reply("Произошла ошибка при обработке данных. Попробуйте позже.")
        await callback_query.answer()  # Закрываем уведомление

    except AttributeError as e:
        logging.error(f"Ошибка атрибута: {e}")
        await callback_query.message.reply("Произошла ошибка при обработке данных. Попробуйте позже.")
        await callback_query.answer()  # Закрываем уведомление

    except TelegramAPIError as e:
        logging.error(f"Ошибка Telegram API: {e}")
        await callback_query.message.reply("Произошла ошибка при взаимодействии с Telegram. Попробуйте позже.")
        await callback_query.answer()  # Закрываем уведомление

    except Exception as e:
        logging.error(f"Произошла непредвиденная ошибка: {e}")
        await callback_query.answer()  # Закрываем уведомление


# ловим промпт в правильном формате
@router.message(StateFilter(FSMPrompt.editing), GoodPromptFilter())
async def get_edited_prompt(message: types.Message, db: Database, state: FSMContext):
    try:
        user_data = await state.get_data()
        if not user_data or 'prompt_id' not in user_data:
            raise ValueError("Не удалось получить значение из состояния")

        prompt_id = user_data.get('prompt_id')
        prompt_text = message.text

        # Редактирование промпта в базе данных
        try:
            await db.edit_user_prompt(prompt_id, prompt_text)
        except Exception as e:
            logging.error(f"Ошибка при редактировании промпта с id {prompt_id}: {e}")
            await message.reply("Произошла ошибка при редактировании промпта. Попробуйте позже.")
            return

        await message.answer("Промпт отредактирован.")

        # Очистка состояния
        try:
            await state.clear()
        except Exception as e:
            logging.error(f"Ошибка при очистке состояния: {e}")
            await message.reply("Произошла ошибка при завершении операции. Попробуйте позже.")
            return

    except TypeError as e:
        logging.error(f"Ошибка типа данных: {e}")
        await message.reply("Произошла ошибка типа данных. Попробуйте позже.")

    except ValueError as e:
        logging.error(f"Ошибка значения: {e}")
        await message.reply("Произошла ошибка при обработке данных. Попробуйте позже.")

    except TelegramAPIError as e:
        logging.error(f"Ошибка Telegram API: {e}")
        await message.reply("Произошла ошибка при взаимодействии с Telegram. Попробуйте позже.")

    except Exception as e:
        logging.error(f"Произошла непредвиденная ошибка: {e}")
        await message.reply("Произошла непредвиденная ошибка. Попробуйте позже.")


# и в неправильном
@router.message(StateFilter(FSMPrompt.editing), ~CommandFilter())  # если это не команда
async def get_edited_prompt(message: types.Message, state: FSMContext):
    try:
        await message.answer("Недопустимый промпт! Попробуйте снова или отмените редактирование командой /cancel")
    except TelegramAPIError as e:
        logging.error(f"Ошибка при отправке сообщения: {e}")
        await message.answer("Ошибка при отправке сообщения. Попробуйте позже.")


# тут он зацикливается, и другие команды не сработают, пока не выйдем из этого состояния

@router.callback_query(MyCallbackFactory.filter(F.action == 'use'))
async def use_prompt(callback_query: types.CallbackQuery, callback_data: MyCallbackFactory, db: Database,
                     state: FSMContext):
    try:
        # Проверка наличия callback_data
        if not callback_data or not hasattr(callback_data, 'prompt_id'):
            await callback_query.answer(f"Не задан промпт для применения!")
            return

        prompt_id = callback_data.prompt_id

        # Получение промпта по id из базы данных
        try:
            prompt = await db.get_prompt_by_id(prompt_id)
            if not prompt:
                raise ValueError("Промпт не найден в базе данных.")
        except Exception as e:
            logging.error(f"Ошибка при получении промпта по id {prompt_id}: {e}")
            await callback_query.message.reply("Произошла ошибка при получении данных. Попробуйте позже.")
            await callback_query.answer()  # Закрываем уведомление
            return

        # Проверка наличия необходимых атрибутов у промпта
        if not hasattr(prompt, 'id') or not hasattr(prompt, 'prompt'):
            raise AttributeError(f"У промпта отсутствуют необходимые атрибуты: {prompt}")

        await state.update_data(prompt_text=prompt.prompt)
        await callback_query.message.answer(
            f"Использование промпта:\n{prompt.prompt}\nДля его отмены пришлите команду /cancel")
        await state.set_state(FSMPrompt.using)
        await callback_query.answer()  # пусто, чтобы не мигала кнопка

    except ValueError as e:
        logging.error(f"Ошибка значения: {e}")
        await callback_query.message.reply("Произошла ошибка при обработке данных. Попробуйте позже.")

    except AttributeError as e:
        logging.error(f"Ошибка атрибута: {e}")
        await callback_query.message.reply("Произошла ошибка при обработке данных. Попробуйте позже.")

    except TelegramAPIError as e:
        logging.error(f"Ошибка Telegram API: {e}")
        await callback_query.message.reply("Произошла ошибка при взаимодействии с Telegram. Попробуйте позже.")

    except Exception as e:
        logging.error(f"Произошла непредвиденная ошибка: {e}")
        await callback_query.message.reply("Произошла непредвиденная ошибка. Попробуйте позже.")

    finally:
        await callback_query.answer()  # Закрываем уведомление


@router.callback_query(MyCallbackFactory.filter(F.action == 'delete'))
async def delete_prompt(callback_query: types.CallbackQuery, callback_data: MyCallbackFactory, db: Database):
    try:
        # Проверка наличия callback_data
        if not callback_data or not hasattr(callback_data, 'prompt_id'):
            await callback_query.answer(f"Не задан промпт для применения!")
            return

        prompt_id = callback_data.prompt_id

        if await db.delete_user_prompt(prompt_id):
            await callback_query.answer(f"Промпт удален")
        else:
            await callback_query.answer(f"Ошибка при удалении промпта. Попробуйте позже.")
        # Закрытие уведомления о нажатии на кнопку
        await callback_query.answer()

    except Exception as e:
        logging.error(f"Произошла ошибка при удалении промпта: {e}")
        await callback_query.message.reply("Произошла ошибка при удалении промпта. Попробуйте позже.")
        await callback_query.answer()  # Закрываем уведомление


# используем промпт, прибавляя его ко всем полученным сообщениям, пока не получим команду /cancel
# в этом случае текст может быть короче или даже состоять из точки или дефиса
# добавляю обработку фото
@router.message(StateFilter(FSMPrompt.using), (F.text.len() <= config.max_query_len) | F.photo)
async def add_prompt_to_query(message: Message, db: Database, state: FSMContext):
    try:
        # Получение данных состояния пользователя
        user_data = await state.get_data()
        if not user_data or 'prompt_text' not in user_data:
            raise ValueError("Не удалось получить значение 'prompt_text' из состояния")

        prompt_text = user_data.get('prompt_text')

        # Проверка типа сообщения и его содержания
        if message.text:
            query_text = f"{prompt_text} \n {message.text}"
            try:
                await process_query(message, db, query_text)
            except Exception as e:
                logging.error(f"Ошибка при обработке запроса с текстом: {e}")
                await message.reply("Произошла ошибка при обработке текста запроса. Попробуйте позже.")
        elif message.photo:
            try:
                await process_photo(message, db, prompt_text)
            except Exception as e:
                logging.error(f"Ошибка при обработке фото: {e}")
                await message.reply("Произошла ошибка при обработке фото. Попробуйте позже.")
        else:
            await message.reply("Некорректное сообщение. Пожалуйста, отправьте текст или фото.")

    except ValueError as e:
        logging.error(f"Ошибка значения: {e}")
        await message.reply("Произошла ошибка при обработке данных. Попробуйте позже.")

    except TelegramAPIError as e:
        logging.error(f"Ошибка Telegram API: {e}")
        await message.reply("Произошла ошибка при взаимодействии с Telegram. Попробуйте позже.")

    except Exception as e:
        logging.error(f"Произошла непредвиденная ошибка: {e}")
        await message.reply("Произошла непредвиденная ошибка. Попробуйте позже.")


@router.message(F.photo)
async def send_photo(message: Message, db: Database):
    try:
        await process_photo(message, db, None)
    except Exception as e:
        logging.error(f"Ошибка при обработке фото: {e}")
        await message.reply("Произошла ошибка при обработке фото. Попробуйте позже.")

@router.message(Command(commands=['admin']), IsAdminFilter())
async def admin(message: Message, db: Database):
    try:
        n_users = await db.get_users_count()
        await message.answer(f"Всего пользователей: {n_users}")

        n_requests = await db.get_requests_count()
        await message.answer(f"Запросов за сегодня: {n_requests}")

        top_users = await db.get_top_users(order_by='daily_requests')
        if top_users:
            table = make_table(top_users, order_by='daily_requests')
            await message.answer("Топ-10 пользователей по количеству запросов за сегодня:\n" + table)
        else:
            await message.answer("Не удалось получить статистику")

        top_users = await db.get_top_users(order_by='total_requests')
        if top_users:
            table = make_table(top_users, order_by='total_requests')
            await message.answer("Топ-10 пользователей по количеству запросов за все время:\n" + table)
        else:
            await message.answer("Не удалось получить статистику")
    except Exception as e:
        logging.error(f"Ошибка при получении статистики по запросам: {e}")
        await message.answer("Произошла ошибка при получении статистики.")


def make_table(top_users, order_by: str = 'daily_requests'):
    table_header = "<b>User ID</b> | <b>Telegram ID</b> | <b>Requests</b>\n"
    table_divider = '-' * 40 + '\n'
    table_body = ""
    for user in top_users:
        if not hasattr(user, 'user_id') or not hasattr(user, 'telegram_id') or not hasattr(user, order_by):
            logging.error(f"Некорректные или отсутствующие данные пользователя: {user}")
            continue
        requests_count = getattr(user, order_by)
        table_body += f"{user.user_id} | {user.telegram_id} | {requests_count}\n"
    return table_divider + table_header + table_divider + table_body + table_divider


@router.message(Command(commands=['admin']))
async def admin(message: Message):
    try:
        logging.warning("Кто-то пытался получить доступ к панели администратора")
    except Exception as e:
        logging.error(f"Я не смог даже залогировать предупреждение о несанкционированном доступе по причине {e}")

@router.message(F.text.startswith("/"), ~CommandFilter())
async def wrong_command(message: Message):
    try:
        await message.reply("Команда не распознана. Для просмотра справки пришлите /help")
    except Exception as e:
        logging.error(f"Ошибка при обработке нераспознанной команды: {e}")
        await message.reply("Произошла ошибка при обработке команды.")

# Хэндлер для обработки документов и других типов файлов
@router.message(F.document | F.audio | F.video | F.voice | F.animation)
async def handle_files(message: Message):
    try:
        await message.reply("Неподдерживаемый тип файлов")
    except Exception as e:
        logging.error(f"Ошибка при обработке неподдерживаемого файла: {e}")
        await message.reply("Произошла ошибка при обработке команды.")

# в любой непонятной ситуации работай просто как мостик к нейросети
# лишь бы длина сообщения позволяла
@router.message(F.text, GoodPromptFilter())
async def default_dialog(message: Message, db: Database):
    try:
        await process_query(message, db, message.text)
    except Exception as e:
        logging.error(f"Ошибка при диалоге: {e}")
        await message.reply("Произошла ошибка при обработке сообщения. Попробуйте позже.")


# если ни один фильтр не сработал + длина сообщения недопустимая
@router.message()
async def default_dialog(message: Message):
    try:
        await message.reply("Недопустимая длина сообщения!")
    except TelegramAPIError as e:
        logging.error("Ошибка при отправке сообщения: {e}")
        await message.reply("Ошибка при отправке сообщения. Попробуйте позже.")
