from aiogram.fsm.state import StatesGroup, State


class MailingSG(StatesGroup):
    choose_type = State()