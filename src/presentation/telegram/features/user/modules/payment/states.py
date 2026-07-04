from aiogram.fsm.state import StatesGroup, State


class PaymentSG(StatesGroup):
    select_method = State()
    waiting_payment = State()
