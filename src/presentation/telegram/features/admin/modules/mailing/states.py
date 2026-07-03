from aiogram.fsm.state import StatesGroup, State


class MailingSG(StatesGroup):
    choose_type = State()
    choose_region = State()
    compose = State()
    confirm = State()