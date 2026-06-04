from aiogram.fsm.state import StatesGroup, State


class CreateRegionSG(StatesGroup):
    title = State()
    timezone = State()
    channel_id = State()
    channel_username = State()
    confirm = State()
