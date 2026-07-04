from aiogram.fsm.state import StatesGroup, State


class UserMenuSG(StatesGroup):
    menu = State()
    chooise_region = State()
