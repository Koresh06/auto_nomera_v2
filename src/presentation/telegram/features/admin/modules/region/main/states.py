from aiogram.fsm.state import StatesGroup, State


class MainRegionSG(StatesGroup):
    start = State()          # 📋 Список регионов / ➕ Создать регион
    list = State()           # список регионов, нажал -> detail
    detail = State()         # карточка региона: инфа + кнопки