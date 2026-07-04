from aiogram.fsm.state import StatesGroup, State


class EditAdSG(StatesGroup):
    list = State()
    detail = State()
    edit_field = State()
    confirm_edit = State()
