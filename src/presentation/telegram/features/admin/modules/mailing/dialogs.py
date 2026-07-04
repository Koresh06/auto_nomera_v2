from aiogram.enums import ButtonStyle, ContentType
from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.kbd import (
    Button,
    Select,
    Group,
    Column,
    Back,
    Cancel,
    SwitchTo,
)
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.style import Style

from .states import MailingSG
from .getters import (
    regions_getter,
    mailing_confirm_getter,
)
from .handlers import (
    on_choose_type,
    on_choose_region,
    on_message_received,
    on_mailing_confirm,
)

mailing_dialog = Dialog(
    Window(
        Const("📢 <b>Меню рассылки</b>\n\nВыберите тип:"),
        Group(
            Button(
                Const("🧍 Всем пользователям"),
                id="all",
                on_click=on_choose_type,
            ),
            Button(
                Const("🌍 По региону"),
                id="region",
                on_click=on_choose_type,
            ),
            Button(
                Const("📢 Во все каналы"),
                id="all_regions",
                on_click=on_choose_type,
            ),
            width=1,
        ),
        Cancel(
            Const("⬅️ Назад"),
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        state=MailingSG.choose_type,
    ),
    Window(
        Const("🌍 Выберите регион:"),
        Group(
            Select(
                Format("{item.title}"),
                id="region_select",
                item_id_getter=lambda item: item.id,
                items="regions",
                on_click=on_choose_region,
            ),
            width=1,
        ),
        Back(
            Const("⬅️ Назад"),
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        state=MailingSG.choose_region,
        getter=regions_getter,
    ),
    Window(
        Const(
            "📝 Отправьте сообщение для рассылки.\n\n"
            "Текст, фото, видео, документ — любой тип. "
            "После отправки покажу предпросмотр."
        ),
        MessageInput(
            func=on_message_received,
            content_types=ContentType.ANY,
        ),
        SwitchTo(
            Const("⬅️ Назад"),
            id="back",
            state=MailingSG.choose_type,
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        state=MailingSG.compose,
    ),
    Window(
        Format(
            "☝️ Так будет выглядеть рассылка.\n\n"
            "📨 Тип: <b>{mail_type_display}</b>\n"
            "{region_display}\n\n"
            "✅ Запустить рассылку?"
        ),
        Column(
            Button(
                Const("🚀 Отправить"),
                id="confirm_send",
                on_click=on_mailing_confirm,
            ),
            Back(Const("✏️ Изменить сообщение")),
            Cancel(Const("❌ Отменить")),
        ),
        state=MailingSG.confirm,
        getter=mailing_confirm_getter,
    ),
)
