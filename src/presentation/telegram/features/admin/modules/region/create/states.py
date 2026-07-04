from aiogram.fsm.state import StatesGroup, State


class CreateRegionSG(StatesGroup):
    title = State()
    timezone = State()
    channel_id = State()
    channel_username = State()
    tg_group_url = State()
    vk_group_url = State()
    max_channel_url = State()
    confirm = State()
