from aiogram.fsm.state import StatesGroup, State


class StatsReplenishmentSG(StatesGroup):
    general = State()
    regions_list = State()
    region_detail = State()
