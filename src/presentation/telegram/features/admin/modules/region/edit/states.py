from aiogram.fsm.state import StatesGroup, State

class EditRegionSettingsSG(StatesGroup):
    menu = State()
    slot_times = State()        
    days_range = State()
    system_paid_slots_count = State()
    publication_limit_enabled = State()
    paid_slot_price = State()
    confirm = State()


class EditRegionMetadataSG(StatesGroup):
    menu = State()
    tg_group_url = State()
    vk_group_url = State()
    max_channel_url = State()
    confirm = State()