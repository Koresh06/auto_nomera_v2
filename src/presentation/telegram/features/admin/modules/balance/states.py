from aiogram.fsm.state import StatesGroup, State


class UserBalanceAdminSG(StatesGroup):
    start = State()
    show_balance = State()
    change_balance = State()
    confirm = State()
