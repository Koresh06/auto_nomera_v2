from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, StartMode

from src.presentation.telegram.features.user.modules.catalog_deferred_publication.states import CatalogDeferredPublishSG


router = Router()


@router.callback_query(F.data == "catalog_deferred_publication")
async def catalog_deferred_publication(
    callback: CallbackQuery,
    dialog_manager: DialogManager,
) -> None:
    await dialog_manager.start(
            CatalogDeferredPublishSG.start,
            mode=StartMode.RESET_STACK,
        )