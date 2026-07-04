from aiogram.fsm.state import StatesGroup, State


class PaidServiceSG(StatesGroup):
    start = State()
    connected = State()


class BuyServiceSG(StatesGroup):
    select_ad = State()
    confirm = State()


class PrePublicationSG(StatesGroup):
    confirm = State()
