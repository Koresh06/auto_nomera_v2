from aiogram_dialog import DialogManager


async def confirm_region_getter(dialog_manager: DialogManager, **kwargs):
    return {
        "title": dialog_manager.find("title").get_value(),
        "timezone": dialog_manager.find("timezone").get_value(),
        "channel_id": dialog_manager.find("channel_id").get_value(),
        "channel_username": dialog_manager.find("channel_username").get_value(),
    }