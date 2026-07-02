from aiogram.fsm.state import StatesGroup, State


class PublishStatsSG(StatesGroup):
    start = State()