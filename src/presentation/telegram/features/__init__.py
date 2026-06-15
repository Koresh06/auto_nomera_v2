from aiogram import Router
from aiogram_dialog import Dialog

from src.presentation.telegram.features.error_handlers import router as error_router
from src.presentation.telegram.features.user.routers import router as user_router
from src.presentation.telegram.features.admin.routers import router as region_router
from src.presentation.telegram.features.admin.modules.urgent_buyout.router import router as admin_urgent_buyout_router
from src.presentation.telegram.features.user.modules.urgent_buyout.routers import router as user_urgent_buyout_router

from src.presentation.telegram.features.user.modules.menu.dialog import user_menu_dialog
from src.presentation.telegram.features.user.modules.ad.create_ad.dialog import create_ad_dialog
from src.presentation.telegram.features.admin.modules.main.dialog import main_region_dialog
from src.presentation.telegram.features.admin.modules.region.create.dialog import create_region_dialog
from src.presentation.telegram.features.user.modules.ad.edit.dialog import edit_ad_dialog
from src.presentation.telegram.features.user.modules.urgent_buyout.dialogs import catalog_deferred_publication_dialog


def get_all_routers() -> list[Router]:
    return [
        error_router,
        user_router,
        region_router,
        admin_urgent_buyout_router,
        user_urgent_buyout_router,
    ]


def get_all_dialogs() -> list[Dialog]:
    return [
        user_menu_dialog,
        create_ad_dialog,
        main_region_dialog,
        create_region_dialog,
        edit_ad_dialog,
        catalog_deferred_publication_dialog
    ]
