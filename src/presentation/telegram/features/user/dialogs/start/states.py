from aiogram.fsm.state import StatesGroup, State


class StartSG(StatesGroup):
    menu = State()
    chooise_region = State()
