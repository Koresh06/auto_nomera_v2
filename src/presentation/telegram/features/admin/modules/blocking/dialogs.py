from aiogram import F
from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.kbd import Button, Back, Cancel
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.input import TextInput

from .states import UserBlockSG
from .getters import (
    getter_user,
)
from .handlers import (
    on_block_action,
    on_user_id_entered,
)

blocked_user_dialog = Dialog(
    Window(
        Const(
            "🔎 <b>Введите Telegram ID пользователя</b>\n\n"
            "📌 Пример: <code>123456789</code>"
        ),
        TextInput(id="tg_id_input", on_success=on_user_id_entered),
        Cancel(Const("⬅️ Назад")),
        state=UserBlockSG.start,
    ),
    Window(
        Format(
            "👤 <b>{user.username}</b>\n"
            "🆔 <b>ID:</b> <code>{user.tg_id}</code>\n"
            "📞 <b>Телефон:</b> {user.phone}"
        ),
        Const("\n🚫 <b>Пользователь:</b> Заблокирован", when="is_blocked"),
        Const("\n✅ <b>Пользователь:</b> Активен", when=~F["is_blocked"]),
        Const("💳 <b>Платежи:</b> Заблокированы", when="is_payment_blocked"),
        Const("💳 <b>Платежи:</b> Активны", when=~F["is_payment_blocked"]),
        Button(
            Const("🚫 Заблокировать"),
            id="block_user",
            on_click=on_block_action,
            when=~F["is_blocked"],
        ),
        Button(
            Const("✅ Разблокировать"),
            id="unblock_user",
            on_click=on_block_action,
            when="is_blocked",
        ),
        Button(
            Const("🚫 Заблокировать платежи"),
            id="block_pay",
            on_click=on_block_action,
            when=~F["is_payment_blocked"],
        ),
        Button(
            Const("✅ Разблокировать платежи"),
            id="unblock_pay",
            on_click=on_block_action,
            when="is_payment_blocked",
        ),
        Back(Const("⬅️ Назад")),
        state=UserBlockSG.action,
        getter=getter_user,
    ),
)
