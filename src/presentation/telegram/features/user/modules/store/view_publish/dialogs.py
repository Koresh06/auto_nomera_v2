from aiogram import F
from aiogram.enums.button_style import ButtonStyle
from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.kbd import (
    Column,
    Next,
    Cancel,
    Back,
    Group,
    Select,
    Start,
    Button,
    Url,
)
from aiogram_dialog.widgets.media import DynamicMedia
from aiogram_dialog.widgets.style import Style

from src.presentation.telegram.features.user.modules.menu.states import UserMenuSG
from src.presentation.telegram.features.user.modules.store.main.states import (
    StoreMainSG,
)
from src.presentation.telegram.features.user.modules.store.view_publish.getters import (
    getter_confirm,
    getter_store_preview,
)
from src.presentation.telegram.features.user.modules.store.view_publish.handlers import (
    on_confirm_publish,
)
from src.presentation.telegram.features.user.shared.ad_getters import (
    calendar_getter,
    getter_finish,
    getter_publication_service,
)
from src.presentation.telegram.features.user.shared.ad_handlers import (
    on_back_to_calendar,
    on_pick_slot,
    on_service_paid_selected,
    on_start_dialog,
)

from .states import StoreViewPublishSG

store_view_publish_dialog = Dialog(
    Window(
        Format(
            "✅ <b>Предварительный просмотр объявления:</b>\n\n"
            "🏦 <b>Магазин:</b> {store_name}\n"
            "🌎 <b>Город:</b> {store_city}\n"
            "📲 <b>Связь:</b> {contacts}\n\n"
            "<b>Список доступных номеров:</b>\n\n"
            "{result_lines}"
        ),
        Next(Const("✅ Публикация"), when="has_items"),
        Cancel(
            Const("⬅️ Назад"),
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        state=StoreViewPublishSG.preview,
        getter=getter_store_preview,
    ),
    Window(
        Format(
            "📅 <b>Выберите дату и время публикации:</b>\n"
            "<i>*💰 - платные слоты ({paid_slot_price} руб.) — лучшие позиции для тех, кто хочет продать быстрее и вне очереди.</i>"
        ),
        Group(
            Select(
                Format("{item.text}"),
                id="slot_select",
                item_id_getter=lambda i: i.id,
                items="slots",
                on_click=on_pick_slot,
            ),
            width=3,
        ),
        Back(
            Const("⬅️ Назад"),
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        state=StoreViewPublishSG.calendar,
        getter=calendar_getter,
    ),
    Window(
        Format(
            "📢 <b>Подтвердите публикацию:</b>\n\n"
            "🏦 <b>Магазин:</b> {store_name}\n"
            "🌎 <b>Город:</b> {store_city}\n"
            "📲 <b>Связь:</b> {contacts}\n\n"
            "<b>Список доступных номеров:</b>\n\n"
            "{result_lines}\n\n"
            "🕒 <b>Дата публикации</b>: {slot_day} {slot_time}\n\n"
        ),
        Button(
            Const("✅ Подтвердить"),
            id="confirm_publish",
            on_click=on_confirm_publish,
            style=Style(style=ButtonStyle.SUCCESS),
        ),
        Button(
            Const("❌ Отмена"),
            id="back_to_calendar",
            on_click=on_back_to_calendar,
            style=Style(style=ButtonStyle.DANGER),
        ),
        state=StoreViewPublishSG.confirm,
        getter=getter_confirm,
    ),
    Window(
        Const(
            "💎 <b>Сделайте своё объявление заметнее! Выберите услуги, чтобы выделить его перед публикацией:</b>"
        ),
        Group(
            Select(
                Format("{item[0]}"),
                id="selected_services",
                item_id_getter=lambda x: str(x[1]),
                items="available_services",
                on_click=on_service_paid_selected,
                style=Style(style=ButtonStyle.SUCCESS),
            ),
            width=1,
        ),
        Next(Const("⏭ Пропустить")),
        state=StoreViewPublishSG.publication_service,
        getter=getter_publication_service,
    ),
    Window(
        Format(
            "✅ Ваше объявление о продаже будет опубликовано {slot_day} в {slot_time} в нашем телеграм канале - <a href='https://t.me/{channel_username}'>{region_title}</a>\n",
            when=~F["is_auto_pub"],
        ),
        Format(
            "✅ Ваше объявление о продаже опубликовано в нашем телеграм канале: <a href='https://t.me/{channel_username}'>{region_title}</a>\n",
            when="is_auto_pub",
        ),
        Format("🔝 Подключённые услуги:\n{selected_services}.\n"),
        Const(
            "<b><u>Так же рекомендуем разместить объявление на сайте:</u></b>\n\n"
            "🌐 Наш сайт: <a href='https://snomerami.ru/'><b>www.snomerami.ru</b></a>\n\n"
            "⚠️ Аудитория сайта и Telegram частично отличается, поэтому объявления получают дополнительный охват и больше потенциальных просмотров"
        ),
        DynamicMedia(selector="media", when="media"),
        Column(
            Url(
                Const("🌐 Разместить на нашем сайте"),
                url=Const("https://snomerami.ru/"),
                style=Style(style=ButtonStyle.DANGER),
            ),
            Back(
                Const("⬅️ Вернуться к услугам"),
                style=Style(style=ButtonStyle.SUCCESS),
            ),
            Start(
                Const("🏦 Мой магазин"),
                id="my_store",
                state=StoreMainSG.main,
            ),
            Start(
                Const("🏠 Главное меню"),
                id="menu",
                state=UserMenuSG.menu,
                style=Style(style=ButtonStyle.PRIMARY),
            ),
        ),
        state=StoreViewPublishSG.finish,
        getter=getter_finish,
    ),
    on_start=on_start_dialog,
)
