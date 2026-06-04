from aiogram.fsm.state import StatesGroup, State


class UserMenuSG(StatesGroup):
    menu = State()
    catalog_urgent_redemption = State()
    sell = State()
    urgent = State()
    buy = State()
    my_store = State()
    create_store = State()
    edit_ad = State()
    paid_services = State()
    profile = State()
    top_up = State()
