from aiogram.fsm.state import StatesGroup, State


class StoreEditSG(StatesGroup):
    start = State()
    name = State()
    city = State()
    phone = State()
    confirm = State()
