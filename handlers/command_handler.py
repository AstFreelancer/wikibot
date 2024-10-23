import logging
from aiogram import Router, F
from aiogram.enums import ContentType
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, LabeledPrice, PreCheckoutQuery

from FSM import FSMPrompt
from database.db import Database
from aiogram.handlers import PreCheckoutQueryHandler

router = Router()


@router.message(Command(commands=['cancel']))
async def cancel(message: Message, state: FSMContext):
    try:
        await message.reply("Команда отменена")

        # Проверка состояния и его очистка
        current_state = await state.get_state()
        if current_state is not None:
            await state.clear()
    except Exception as e:
        # Логирование ошибок
        logging.error(f"Ошибка при обработке команды /cancel: {e}")
        await message.reply("Произошла ошибка при обработке команды.")


@router.message(Command(commands=['start']))
async def send_welcome(message: Message, db: Database):
    try:
        #    user_language = message.from_user.language_code
        user_id = message.from_user.id
        await db.add_user(user_id)
        logging.info(f"Зарегистрирован пользователь {user_id}, если его не было в БД")
        await message.reply(f"Привет! Пришлите запрос или выберите промпт.\n")
    except Exception as e:
        logging.error(f"Ошибка при выполнении команды /start: {e}")
        await message.reply("Произошла ошибка при обработке команды.")


@router.message(Command(commands=['help']))
async def send_help(message: Message):
    try:
        await message.reply(f"Команды:\n"
                            "/buy - купить подписку\n"
                            "/prompts - показать мои промпты\n"
                            "/add - добавить новый промпт\n"
                            "/edit - редактировать промпт\n"
                            "/delete - удалить промпт\n"
                            "/cancel - отменить команду")
    except Exception as e:
        logging.error(f"Ошибка при выполнении команды /help: {e}")
        await message.reply("Произошла ошибка при обработке команды.")


@router.message(Command(commands=['buy']))
async def buy_subscription(message: Message, state: FSMContext, db: Database):
    try:
        last_payment_date = await db.get_last_payment_date(message.from_user.id)
        if last_payment_date is not None:
            formatted_date = last_payment_date.strftime("%d-%m-%Y")
            await message.answer(f"Ваша подписка активна с {formatted_date}.")
        else:
            # Проверка состояния и его очистка
            current_state = await state.get_state()
            if current_state is not None:
                await state.clear()  # чтобы свободно перейти сюда из любого другого состояния

            from config import config
            if config.provider_token.split(':')[1] == 'TEST':
                await message.reply("Для оплаты используйте данные тестовой карты: 1111 1111 1111 1026, 12/22, CVC 000.")

            prices = [LabeledPrice(label='Оплата заказа', amount=config.price)]

            await state.set_state(FSMPrompt.buying)
            from loader import bot
            await bot.send_invoice(
                chat_id=message.chat.id,
                title='Покупка подписки',
                description='Оплата подписки на месяц',
                payload='subscription',
                provider_token=config.provider_token,
                currency=config.currency,
                start_parameter='test',
                prices=prices
            )
    except Exception as e:
        logging.error(f"Ошибка при выполнении команды /buy: {e}")
        await message.reply("Произошла ошибка при обработке команды.")


# стандартный код для обработки апдейта типа PreCheckoutQuery, на который нам необходимо ответить в течение десяти секунд
@router.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery):
    try:
        from loader import bot
        await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)  # всегда отвечаем утвердительно
    except Exception as e:
        logging.error(f"Ошибка при обработке апдейта типа PreCheckoutQuery: {e}")


@router.message(F.successful_payment)
async def process_successful_payment(message: Message, state: FSMContext, db: Database):
    try:
        await message.reply(f"Платеж на сумму {message.successful_payment.total_amount // 100} "
                            f"{message.successful_payment.currency} прошел успешно!")
        await db.update_payment(message.from_user.id)
        logging.info(f"Получен платеж от {message.from_user.id}")
        current_state = await state.get_state()
        if current_state is not None:
            await state.clear()  # чтобы свободно перейти сюда из любого другого состояния
    except Exception as e:
        logging.error(f"Ошибка при отправке сообщения об успешном платеже: {e}")


@router.message(StateFilter(FSMPrompt.buying))
async def process_unsuccessful_payment(message: Message, state: FSMContext):
    try:
        await message.reply(f"Не удалось выполнить платеж!")
        current_state = await state.get_state()
        if current_state is not None:
            await state.clear()  # чтобы свободно перейти сюда из любого другого состояния

    except Exception as e:
        logging.error(f"Ошибка при отправке сообщения о неуспешном платеже: {e}")
