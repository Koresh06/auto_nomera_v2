from aiogram.fsm.state import StatesGroup, State


class StoreCreateSG(StatesGroup):
    confirm_create = State()
    name = State()
    city = State()
    phone = State()
    confirm_store = State()
    message_final = State()