from aiogram import Router
from aiogram_dialog import Dialog

from src.presentation.telegram.features.user.routers import router as user_router
from src.presentation.telegram.features.user.dialogs.create_ad.dialog import create_ad_dialog


def get_all_routers() -> list[Router]:
    return [
        user_router,
    ]


def get_all_dialogs() -> list[Dialog]:
    return [
        create_ad_dialog,
    ]