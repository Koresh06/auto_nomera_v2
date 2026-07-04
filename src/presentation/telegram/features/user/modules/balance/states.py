from aiogram.fsm.state import StatesGroup, State


class TopupSG(StatesGroup):
    enter_amount = State()
