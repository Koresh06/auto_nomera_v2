from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import Back, Cancel, Next, Button


from src.presentation.telegram.features.admin.views.region.create.getters import (
    confirm_region_getter,
)
from src.presentation.telegram.features.admin.views.region.create.handlers import on_confirm_region
from src.presentation.telegram.features.admin.views.region.create.states import (
    CreateRegionSG,
)
from src.presentation.telegram.features.admin.views.region.create.validators import (
    validate_channel_id,
    validate_channel_username,
    validate_timezone,
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
        Const("Подтвердите создание региона"),
        Format(
            "Название: {title}\n"
            "Часовой пояс: {timezone}\n"
            "ID канала: {channel_id}\n"
            "Username канала: {channel_username}",
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
