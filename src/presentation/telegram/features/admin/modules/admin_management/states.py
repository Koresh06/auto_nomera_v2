from aiogram.fsm.state import StatesGroup, State


class AdminManagementSG(StatesGroup):
    menu = State()
    admin_detail = State()
    add_input = State()
    add_confirm = State()
