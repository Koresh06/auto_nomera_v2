from aiogram.fsm.state import StatesGroup, State


class StatsExportSG(StatesGroup):
    menu = State()
    period = State()
    custom_dates = State()
    regions = State()
    sections = State()
    preview = State()
