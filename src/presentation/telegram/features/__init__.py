from aiogram import Router
from aiogram_dialog import Dialog

from src.presentation.telegram.features.error_handlers import router as error_router
from src.presentation.telegram.features.user.routers import router as user_router
from src.presentation.telegram.features.admin.routers import router as region_router

from src.presentation.telegram.features.user.views.menu.dialog import user_menu_dialog
from src.presentation.telegram.features.user.views.ad.create_ad.dialog import create_ad_dialog
from src.presentation.telegram.features.admin.views.main.dialog import main_region_dialog
from src.presentation.telegram.features.admin.views.region.create.dialog import create_region_dialog
from src.presentation.telegram.features.user.views.ad.edit.dialog import edit_ad_dialog


def get_all_routers() -> list[Router]:
    return [
        error_router,
        user_router,
        region_router,
    ]


def get_all_dialogs() -> list[Dialog]:
    return [
        user_menu_dialog,
        create_ad_dialog,
        main_region_dialog,
        create_region_dialog,
        edit_ad_dialog,
    ]
