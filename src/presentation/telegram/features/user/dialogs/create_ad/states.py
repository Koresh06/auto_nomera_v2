from aiogram.fsm.state import StatesGroup, State


class CreateAdSG(StatesGroup):
    plate = State()
    city = State()
    price = State()
    contacts = State()
    calendar = State()
    done = State()
