from aiogram.fsm.state import StatesGroup, State


class StoreEditItemsSG(StatesGroup):
    all_list = State()