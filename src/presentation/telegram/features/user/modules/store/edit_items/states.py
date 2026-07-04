from aiogram.fsm.state import StatesGroup, State


class StoreEditItemsSG(StatesGroup):
    all_list = State()
    edit = State()
    edit_plate = State()
    edit_price = State()
    confirm = State()
