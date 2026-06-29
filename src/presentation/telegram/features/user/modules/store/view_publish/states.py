from aiogram.fsm.state import StatesGroup, State


class StoreViewPublishSG(StatesGroup):
    preview = State()
    calendar = State()
    confirm = State()
    publication_service = State()
    finish = State()