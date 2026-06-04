from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.text import Const
from aiogram_dialog.widgets.kbd import Start

from src.presentation.telegram.features.admin.views.main.states import MainRegionSG
from src.presentation.telegram.features.admin.views.region.create.states import (
    CreateRegionSG,
)

main_region_dialog = Dialog(
    Window(
        Const("Меню регионов"),
        Start(
            Const("Создать регион"),
            id="create_region",
            state=CreateRegionSG.title,
        ),
        state=MainRegionSG.start,
    ),
)
