from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.text import Const
from aiogram_dialog.widgets.kbd import Start

from src.presentation.telegram.features.admin.modules.main.states import MainRegionSG
from src.presentation.telegram.features.admin.modules.region.create.states import (
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
