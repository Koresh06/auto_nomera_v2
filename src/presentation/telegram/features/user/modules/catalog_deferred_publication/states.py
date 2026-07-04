from aiogram.fsm.state import StatesGroup, State


class CatalogDeferredPublishSG(StatesGroup):
    start = State()
    list_view = State()
