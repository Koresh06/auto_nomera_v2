from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.kbd import Button, Back, Cancel, Column, SwitchTo
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.input import TextInput

from src.presentation.telegram.features.error_handlers import on_input_error

from .states import (
    UserBalanceAdminSG,
)
from .getters import (
    getter_user_balance,
    getter_confirm,
)
from .handlers import (
    on_user_id_entered,
    on_amount_entered,
    on_balance_confirm,
)
from .validators import (
    validate_signed_amount,
)

admin_balance_dialog = Dialog(
    Window(
        Const(
            "🔎 <b>Введите Telegram ID пользователя</b>\n\n"
            "📌 Пример: <code>123456789</code>"
        ),
        TextInput(
            id="tg_id_input",
            on_success=on_user_id_entered,
        ),
        Cancel(Const("⬅️ Назад")),
        state=UserBalanceAdminSG.start,
    ),
    Window(
        Format(
            "👤 <b>{user.username}</b>\n"
            "🆔 <b>ID:</b> <code>{user.tg_id}</code>\n"
            "💰 <b>Баланс:</b> {balance}\n"
            "📞 <b>Телефон:</b> {user.phone}"
        ),
        SwitchTo(
            Const("💸 Изменить баланс"),
            id="to_change",
            state=UserBalanceAdminSG.change_balance,
        ),
        Back(Const("⬅️ Назад")),
        state=UserBalanceAdminSG.show_balance,
        getter=getter_user_balance,
    ),
    Window(
        Const(
            "<b>Введите сумму со знаком:</b>\n\n"
            "📈 <code>+500</code> — начислить\n"
            "📉 <code>-200</code> — списать"
        ),
        TextInput(
            id="balance_input",
            type_factory=validate_signed_amount,
            on_success=on_amount_entered,
            on_error=on_input_error,
        ),
        Back(Const("⬅️ Назад")),
        state=UserBalanceAdminSG.change_balance,
    ),
    Window(
        Format(
            "⚠️ <b>Подтвердите операцию:</b>\n\n"
            "👤 <b>ID:</b> <code>{tg_id}</code>\n"
            "💰 <b>Текущий баланс:</b> {current_balance} руб.\n"
            "{operation}: <b>{abs_amount} руб.</b>"
        ),
        Column(
            Button(
                Const("✅ Подтвердить"),
                id="confirm_balance",
                on_click=on_balance_confirm,
            ),
            Back(Const("❌ Отменить")),
        ),
        state=UserBalanceAdminSG.confirm,
        getter=getter_confirm,
    ),
)
