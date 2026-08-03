from aiogram import F
from aiogram.enums.button_style import ButtonStyle
from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.style import Style
from aiogram_dialog.widgets.text import Format, Const, List
from aiogram_dialog.widgets.kbd import Cancel, Group, Select, Column, Button, Back

from .states import UnpublishedAdsSG
from .getters import getter_overdue_slots
from .handlers import getter_unpublished_by_slot, on_pick_slot, on_publish_all

unpublished_publications_dialog = Dialog(
    Window(
        Format(
            "🗂 <b>Неопубликованные объявления сегодня</b>\n\n"
            "Выберите время слота для проверки:",
        ),
        Const("✅ Все публикации сегодня опубликованы вовремя", when=~F["has_slots"]),
        Group(
            Select(
                Format("{item[0]} ({item[1]})"),
                id="slot_select",
                item_id_getter=lambda x: x[0],
                items="slots",
                on_click=on_pick_slot,
            ),
            width=3,
            when="has_slots",
        ),
        Cancel(
            Const("⬅️ Назад"),
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        state=UnpublishedAdsSG.pick_slot,
        getter=getter_overdue_slots,
    ),
    Window(
        Format(
            "🗂 <b>Неопубликованные объявления</b>\n"
            "Всего: <b>{count}</b>\n"
            "Слот: <b>{slot}</b>\n",
        ),
        Const("✅ Все опубликованы", when=~F["has_ads"]),
        List(
            Format(
                "<b>{item[plate_number]}</b> {item[owner_link]} — {item[ad_type_display]}"
            ),
            items="ads",
            sep="\n",
            id="ads_list",
            when="has_ads",
        ),
        Column(
            Button(
                Const("🚀 Опубликовать всё"),
                id="publish_all",
                on_click=on_publish_all,
                when="has_ads",
            ),
            Back(
                Const("⬅️ Назад"),
                style=Style(style=ButtonStyle.PRIMARY),
            ),
        ),
        state=UnpublishedAdsSG.view,
        getter=getter_unpublished_by_slot,
        disable_web_page_preview=True,
    ),
)
