from aiogram_dialog.api.protocols import DialogManager
from aiogram_dialog.widgets.common import (
    BaseScroll,
    OnPageChangedVariants,
    WhenCondition,
)
from aiogram_dialog.widgets.text import Text


class SmartScrollingText(Text, BaseScroll):
    def __init__(
        self,
        text: Text,
        id: str,
        items_per_page: int = 3,  # сколько карточек показывать на одной странице
        when: WhenCondition = None,
        on_page_changed: OnPageChangedVariants = None,
    ):
        Text.__init__(self, when=when)
        BaseScroll.__init__(self, id=id, on_page_changed=on_page_changed)
        self.text = text
        self.items_per_page = items_per_page

    async def _render_contents(self, data: dict, manager: DialogManager) -> list[str]:
        text = await self.text.render_text(data, manager)
        return [t.strip() for t in text.split("\n\n") if t.strip()]

    async def _render_text(self, data, manager: DialogManager) -> str:
        cards = await self._render_contents(data, manager)
        total_cards = len(cards)
        total_pages = max(1, (total_cards + self.items_per_page - 1) // self.items_per_page)
        current_page = await self.get_page(manager)
        start = current_page * self.items_per_page
        end = start + self.items_per_page
        visible_cards = cards[start:end]

        data["page_current"] = current_page + 1  
        data["pages_total"] = total_pages
        data["items_total"] = total_cards
        
        return "\n\n".join(visible_cards)

    async def get_page_count(self, data: dict, manager: DialogManager) -> int:
        cards = await self._render_contents(data, manager)
        return max(1, (len(cards) + self.items_per_page - 1) // self.items_per_page)