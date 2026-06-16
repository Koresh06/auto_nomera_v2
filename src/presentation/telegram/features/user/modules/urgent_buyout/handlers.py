from dishka.integrations.aiogram_dialog import FromDishka, inject
from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Button, Select
from aiogram_dialog.widgets.kbd.select import OnItemClick

from src.application.dtos.user import UserDTO
from src.application.mediator import Mediator
from src.application.use_cases.ad.archive_ad import ArchiveAdRequest
from src.application.use_cases.catalog.get_catalog_deferred_publications import (
    CatalogItem,
    GetCatalogDeferredPublicationsRequest,
)


@inject
async def on_delete_catalog_item(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
) -> None:
    user: UserDTO = dialog_manager.dialog_data["user"]

    if dialog_manager.dialog_data.get("delete_warning"):
        dialog_manager.dialog_data.pop("delete_warning", None)

        scroll = dialog_manager.find("catalog_scroll")
        current_page = await scroll.get_page() if scroll else 0

        items: list[CatalogItem] = await mediator.handle(
            GetCatalogDeferredPublicationsRequest(region_id=user.region_id)
        )

        if current_page < len(items):
            item = items[current_page]
            await mediator.handle(
                ArchiveAdRequest(
                    ad_id=item.ad.id,
                    publication_id=item.publication.id if item.publication else None,
                )
            )

        await callback.answer("🗑 Объявление удалено.", show_alert=False)
    else:
        dialog_manager.dialog_data["delete_warning"] = True
        await callback.answer(
            "⚠️ Вы уверены? Нажмите ещё раз для подтверждения.",
            show_alert=True,
        )


@inject
async def on_catalog_item_selected(
    callback: CallbackQuery,
    widget: OnItemClick[Select[str], str],
    dialog_manager: DialogManager,
    item_id: str,
    mediator: FromDishka[Mediator],
) -> None:
    await dialog_manager.back()
    scroll = dialog_manager.find("catalog_scroll")
    if scroll:
        await scroll.set_page(int(item_id))
