from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


async def catalog_deferred_publication_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💎 Каталог объявлений до публикации",
                    callback_data="catalog_deferred_publication",
                    style="primary",
                )
            ]
        ]
    )
