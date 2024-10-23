from aiogram.fsm.state import StatesGroup, State


class FSMPrompt(StatesGroup):
    adding = State()
    editing = State()
    using = State()
    buying = State()