from dishka.integrations.aiogram_dialog import FromDishka, inject
from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Button, Select
from aiogram_dialog.widgets.kbd.select import OnItemClick

from src.application.dtos.user import UserDTO
from src.application.mediator import Mediator
from src.application.use_cases.user.get_by_tg_id import GetTgIdRequest
from src.presentation.telegram.features.admin.modules.menu.filter import (
    is_admin_user,
)
from src.presentation.telegram.features.user.modules.catalog_deferred_publication.getters import (
    has_active_pre_publication,
)
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
    # кнопка видна только админам, но скрытая кнопка тоже обрабатывает
    # callback — проверяем права здесь
    if not await is_admin_user(callback.from_user.id, mediator):
        await callback.answer("⛔ Недостаточно прав.", show_alert=True)
        return

    region_id: int = dialog_manager.dialog_data["region_id"]

    if dialog_manager.dialog_data.get("delete_warning"):
        dialog_manager.dialog_data.pop("delete_warning", None)

        scroll = dialog_manager.find("catalog_scroll")
        current_page = await scroll.get_page() if scroll else 0

        items: list[CatalogItem] = await mediator.handle(
            GetCatalogDeferredPublicationsRequest(region_id=region_id)
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
    user: UserDTO = await mediator.handle(GetTgIdRequest(tg_id=callback.from_user.id))
    if not has_active_pre_publication(user):
        await callback.answer(
            "💎 Доступно по подписке «Ранний доступ».", show_alert=True
        )
        return
    await dialog_manager.next()
    scroll = dialog_manager.find("catalog_scroll")
    if scroll:
        await scroll.set_page(int(item_id))
