from aiogram.types import InlineKeyboardButton, CallbackQuery

from aiogram_dialog import DialogManager
from aiogram_dialog.api.internal import RawKeyboard
from aiogram_dialog.api.protocols import DialogProtocol
from aiogram_dialog.widgets.common import WhenCondition
from aiogram_dialog.widgets.common import (
    BaseScroll,
    OnPageChangedVariants,
)
from aiogram_dialog.widgets.kbd.base import Keyboard

from src.presentation.telegram.features.user.modules.urgent_buyout.states import UrgentBououtSG


class CatalogScroll(BaseScroll, Keyboard):
    def __init__(
        self,
        id: str,
        pages_field: str = "count_page",
        current_field: str = "current_page_display",
        when: WhenCondition = None,
        on_page_changed: OnPageChangedVariants = None,
    ):
        BaseScroll.__init__(self, id=id, on_page_changed=on_page_changed)
        Keyboard.__init__(self, id=id, when=when)
        self.pages_field = pages_field
        self.current_field = current_field

    async def get_page_count(self, data: dict, manager: DialogManager) -> int:
        return data.get(self.pages_field, 1)

    async def _render_keyboard(
        self,
        data: dict,
        manager: DialogManager,
    ) -> RawKeyboard:
        if not self.is_(data, manager):
            return []
    
        pages = await self.get_page_count(data, manager)
        if pages <= 1:
            return []
    
        current_page = await self.get_page(manager)
    
        return [
            [
                InlineKeyboardButton(
                    text="⬅️",
                    callback_data=self._item_callback_data(str(current_page - 1)),
                ),
                InlineKeyboardButton(
                    text=f"📄 {current_page + 1} / {pages}",
                    callback_data=self._item_callback_data("list"),
                ),
                InlineKeyboardButton(
                    text="➡️",
                    callback_data=self._item_callback_data(str(current_page + 1)),
                ),
            ]
        ]
    
    async def _process_item_callback(
        self,
        callback: CallbackQuery,
        data: str,
        dialog: DialogProtocol,
        manager: DialogManager,
    ) -> bool:
        if data == "list":
            await manager.switch_to(UrgentBououtSG.list_view)
            return True

        pages = manager.dialog_data.get(self.pages_field, 1)

        requested = int(data)

        if requested < 0:
            requested = pages - 1
        elif requested >= pages:
            requested = 0

        await BaseScroll.set_page(self, callback, requested, manager)
        return True