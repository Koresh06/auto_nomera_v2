from aiogram.fsm.state import StatesGroup, State


class UserBlockSG(StatesGroup):
    start = State()
    action = State()
