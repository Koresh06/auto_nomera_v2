from aiogram.enums.button_style import ButtonStyle
from aiogram_dialog.widgets.style import Style
from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.text import Const
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import Cancel

from src.presentation.telegram.features.error_handlers import on_input_error

from .states import TopupSG
from .handlers import on_amount_input_success

topup_dialog = Dialog(
    Window(
        Const(
            "💰 <b>Пополнение баланса</b>\n\nВведите сумму в рублях (минимум 100 руб.):"
        ),
        TextInput(
            id="amount_input",
            type_factory=str,
            on_success=on_amount_input_success,
            on_error=on_input_error,
        ),
        Cancel(
            Const("🏠 Главное меню"),
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        state=TopupSG.enter_amount,
    ),
)
