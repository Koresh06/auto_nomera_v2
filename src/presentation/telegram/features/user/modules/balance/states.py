from aiogram.fsm.state import StatesGroup, State


class TopupSG(StatesGroup):
    enter_amount = State()
    select_method = State()
    waiting_payment = State()