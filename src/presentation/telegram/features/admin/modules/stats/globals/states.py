from aiogram.fsm.state import StatesGroup, State


class GlobalStatsSG(StatesGroup):
    start = State()
    regions_list = State()
    region_stats = State()
