from aiogram.fsm.state import StatesGroup, State


class CreateAdSG(StatesGroup):
    plate = State()
    duplicate_preview = State()
    image = State()
    city = State()
    price = State()
    phone = State()
    calendar = State()
    confirm = State()
    publication_service = State()
    finish = State()
