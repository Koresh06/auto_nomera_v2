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
        Const("📅 <b>Выберите дату и время публикации:</b>"),
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
            Const("✅ Опубликовать"),
            id="confirm_publish",
            on_click=on_confirm_publish,
        ),
        # Button(
        #     Const("⬅️ Назад"),
        #     id="back_to_calendar",
        #     on_click=on_back_to_calendar,
        #     style=Style(style=ButtonStyle.PRIMARY),
        # ),
        Cancel(
            Const("❌ Отмена"),
            on_click=on_back_to_calendar,
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
            ),
            width=1,
        ),
        Next(Const("⏭ Пропустить")),
        state=StoreViewPublishSG.publication_service,
        getter=getter_publication_service,
    ),
    Window(
        Const("🤝 <b>Спасибо что выбрали Нас.</b>\n\n"),
        Format(
            "✅ Ваше объявление о продаже будет опубликовано {slot_day} в {slot_time} в нашем телеграм канале: <a href='https://t.me/{channel_username}'>{region_title}</a>\n",
            when=~F["is_auto_pub"],
        ),
        Format(
            "✅ Ваше объявление о продаже опубликовано в нашем телеграм канале: <a href='https://t.me/{channel_username}'>{region_title}</a>\n",
            when="is_auto_pub",
        ),
        Const("‼️ Подписывайтесь на канал, чтобы не потерять объявление!\n\n"),
        Const(
            "Для быстрой продажи рекомендуем воспользоваться платными услугами, выбрав раздел «🚀 Платные Топ услуги (NEW)» в общем меню, чтобы выделить Ваше объявление среди других.\n\n"
        ),
        Format("🔝 Подключённые услуги:\n{selected_services}."),
        DynamicMedia(selector="media", when="media"),
        Back(
            Const("Назад к Услугам!"),
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        Column(
            Start(
                Const("🏦 Мой магазин"),
                id="my_store",
                state=StoreMainSG.main,
            ),
            Start(
                Const("🏠 Главное меню"),
                id="menu",
                state=UserMenuSG.menu,
            ),
        ),
        state=StoreViewPublishSG.finish,
        getter=getter_finish,
    ),
)
