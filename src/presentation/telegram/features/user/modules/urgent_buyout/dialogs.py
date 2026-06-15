from aiogram import F
from aiogram_dialog import Dialog, StartMode, Window
from aiogram_dialog.widgets.text import Const
from aiogram_dialog.widgets.kbd import Start


from src.presentation.telegram.features.user.modules.menu.states import UserMenuSG

from .states import UrgentBououtSG
from .getters import urgent_buyout_getter


catalog_deferred_publication_dialog = Dialog(
    Window(
        Const(
            "💎 <b>Каталог срочных выкупов и объявлений до публикации</b>\n\n"
            "😔 В вашем регионе пока нет новых заявок на срочный выкуп.\n"
            '🚀"Объявления до публикации" будут приходить за 2 часа до размещения в нашем канале и чате.',
        ),
        Start(
            Const("🏠 Главное меню"),
            id="general_menu",
            state=UserMenuSG.menu,
            mode=StartMode.RESET_STACK,
        ),
        state=UrgentBououtSG.start,
        getter=urgent_buyout_getter,
    )
)