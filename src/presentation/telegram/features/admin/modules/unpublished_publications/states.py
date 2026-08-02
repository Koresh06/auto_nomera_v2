from aiogram.fsm.state import StatesGroup, State


class UnpublishedAdsSG(StatesGroup):
    pick_slot = State()
    view = State()
