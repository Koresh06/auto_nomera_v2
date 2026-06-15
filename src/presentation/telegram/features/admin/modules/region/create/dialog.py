from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import Back, Cancel, Next, Button


from src.presentation.telegram.features.admin.modules.region.create.getters import (
    confirm_region_getter,
)
from src.presentation.telegram.features.admin.modules.region.create.handlers import (
    on_confirm_region,
)
from src.presentation.telegram.features.admin.modules.region.create.states import (
    CreateRegionSG,
)
from src.presentation.telegram.features.admin.modules.region.create.validators import (
    validate_channel_id,
    validate_channel_username,
    validate_timezone,
    validate_tg_url,
    validate_vk_url,
    validate_max_url,
)
from src.presentation.telegram.features.error_handlers import on_input_error

create_region_dialog = Dialog(
    Window(
        Const("Введите название региона"),
        TextInput(
            id="title",
            type_factory=str,
            on_success=Next(),
        ),
        Cancel(Const("⬅️ Назад")),
        state=CreateRegionSG.title,
    ),
    Window(
        Const(
            "🌍 <b>Введите часовой пояс региона</b>\n\n"
            "Формат: <code>Europe/Moscow</code>\n\n"
            "Примеры:\n"
            "<code>Europe/Moscow</code> — Москва (UTC+3)\n"
            "<code>Europe/Minsk</code> — Минск (UTC+3)\n"
            "<code>Asia/Yekaterinburg</code> — Екатеринбург (UTC+5)\n"
            "<code>Asia/Novosibirsk</code> — Новосибирск (UTC+7)\n"
            "<code>Asia/Krasnoyarsk</code> — Красноярск (UTC+7)\n"
            "<code>Asia/Irkutsk</code> — Иркутск (UTC+8)\n"
            "<code>Asia/Vladivostok</code> — Владивосток (UTC+10)\n"
        ),
        TextInput(
            id="timezone",
            type_factory=validate_timezone,
            on_success=Next(),
            on_error=on_input_error,
        ),
        Back(Const("⬅️ Назад")),
        state=CreateRegionSG.timezone,
    ),
    Window(
        Const(
            "📢 <b>Введите ID канала</b>\n\n"
            "Формат: <code>-1001234567890</code>\n\n"
            "💡 Чтобы узнать ID — перешли любое сообщение из канала боту @userinfobot"
        ),
        TextInput(
            id="channel_id",
            type_factory=validate_channel_id,
            on_success=Next(),
            on_error=on_input_error,
        ),
        Back(Const("⬅️ Назад")),
        state=CreateRegionSG.channel_id,
    ),
    Window(
        Const(
            "🔗 <b>Введите username канала</b>\n\n"
            "Формат: <code>mychannel</code> или <code>@mychannel</code>\n\n"
            "💡 Без пробелов, только латиница, цифры и подчёркивание"
        ),
        TextInput(
            id="channel_username",
            type_factory=validate_channel_username,
            on_success=Next(),
            on_error=on_input_error,
        ),
        Back(Const("⬅️ Назад")),
        state=CreateRegionSG.channel_username,
    ),
    Window(
        Const(
            "💬 <b>Ссылка на группу Telegram</b>\n\n"
            "Формат: <code>https://t.me/mygroup</code>"
        ),
        TextInput(
            id="tg_group_url",
            type_factory=validate_tg_url,
            on_success=Next(),
            on_error=on_input_error,
        ),
        Next(Const("⏭️ Пропустить")),
        Back(Const("⬅️ Назад")),
        state=CreateRegionSG.tg_group_url,
    ),
    Window(
        Const(
            "🔵 <b>Ссылка на группу ВКонтакте</b>\n\n"
            "Формат: <code>https://vk.com/mygroup</code>"
        ),
        TextInput(
            id="vk_group_url",
            type_factory=validate_vk_url,
            on_success=Next(),
            on_error=on_input_error,
        ),
        Next(Const("⏭️ Пропустить")),
        Back(Const("⬅️ Назад")),
        state=CreateRegionSG.vk_group_url,
    ),
    Window(
        Const(
            "📱 <b>Ссылка на канал в Макс</b>\n\n"
            "Формат: <code>https://max.ru/...</code>"
        ),
        TextInput(
            id="max_channel_url",
            type_factory=validate_max_url,
            on_success=Next(),
            on_error=on_input_error,
        ),
        Next(Const("⏭️ Пропустить")),
        Back(Const("⬅️ Назад")),
        state=CreateRegionSG.max_channel_url,
    ),
    Window(
        Const("Подтвердите создание региона"),
        Format(
            "📋 <b>Данные региона:</b>\n\n"
            "🏙️ Название: <b>{title}</b>\n"
            "🌍 Часовой пояс: <b>{timezone}</b>\n"
            "📢 ID канала: <b>{channel_id}</b>\n"
            "🔗 Username канала: <b>{channel_username}</b>\n\n"
            "💬 Telegram группа: <b>{tg_group_url}</b>\n"
            "🔵 ВКонтакте: <b>{vk_group_url}</b>\n"
            "📱 Макс: <b>{max_channel_url}</b>",
        ),
        Button(
            Const("✅ Подтвердить"),
            id="confirm",
            on_click=on_confirm_region,
        ),
        Back(Const("⬅️ Назад")),
        state=CreateRegionSG.confirm,
        getter=confirm_region_getter,
    ),
)
