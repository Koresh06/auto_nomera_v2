from aiogram.fsm.state import StatesGroup, State


class PublishStatsSG(StatesGroup):
    stats = State()           
    regions_list = State()     
    schedule = State()         
    catalog = State()  
    list = State()