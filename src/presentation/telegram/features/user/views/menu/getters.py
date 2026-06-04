from aiogram_dialog import DialogManager


async def getter_user_menu(dialog_manager: DialogManager, **kwargs) -> dict:
    return {
        "is_store": True,
        "region_name": "Москва",
        "is_early_access": True,
    }