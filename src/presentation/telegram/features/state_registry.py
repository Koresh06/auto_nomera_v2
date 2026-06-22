from aiogram.fsm.state import State

from src.presentation.telegram.features.user.modules.ad.create_ad.states import CreateAdSG
from src.presentation.telegram.features.user.modules.menu.states import UserMenuSG
from src.presentation.telegram.features.user.modules.paid_services.states import BuyServiceSG, PrePublicationSG


STATE_REGISTRY: dict[str, State] = {
    "CreateAdSG:confirm": CreateAdSG.confirm,
    "CreateAdSG:calendar": CreateAdSG.calendar,
    "UserMenuSG:menu": UserMenuSG.menu,
    "BuyServiceSG:select_ad": BuyServiceSG.select_ad,
    "PrePublicationSG:confirm": PrePublicationSG.confirm,
}

def resolve_state(key: str) -> State:
    state = STATE_REGISTRY.get(key)
    if state is None:
        raise ValueError(f"Unknown state key for teleport: {key}")
    return state