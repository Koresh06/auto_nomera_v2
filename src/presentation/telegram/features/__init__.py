from aiogram import Router
from aiogram_dialog import Dialog

from src.presentation.telegram.features.user.routers import router as user_router
from src.presentation.telegram.features.admin.routers import router as region_router

from src.presentation.telegram.features.user.views.start.dialog import start_dialog
from src.presentation.telegram.features.user.views.ad.create_ad.dialog import create_ad_dialog
from src.presentation.telegram.features.admin.views.main.dialog import main_region_dialog
from src.presentation.telegram.features.admin.views.region.create.dialog import create_region_dialog


def get_all_routers() -> list[Router]:
    return [
        user_router,
        region_router,
    ]


def get_all_dialogs() -> list[Dialog]:
    return [
        start_dialog,
        create_ad_dialog,
        main_region_dialog,
        create_region_dialog,
    ]
