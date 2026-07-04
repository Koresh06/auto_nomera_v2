from aiogram.fsm.state import StatesGroup, State


class PaidServiceAdminSG(StatesGroup):
    list = State()
    detail = State()
    edit_price = State()
    edit_duration = State()
    edit_description = State()
    edit_title = State()
