from aiogram.fsm.state import StatesGroup, State


class UserBalanceAdminSG(StatesGroup):
    start = State()