from aiogram.fsm.state import StatesGroup, State


class StoreViewPublishSG(StatesGroup):
    view = State()