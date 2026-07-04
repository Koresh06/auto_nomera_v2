from aiogram.fsm.state import StatesGroup, State


class StoreAddItemsSG(StatesGroup):
    enter = State()
    preview = State()
    result = State()
