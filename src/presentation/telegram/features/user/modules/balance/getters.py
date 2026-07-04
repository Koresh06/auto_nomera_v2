from aiogram_dialog import DialogManager

from src.domain.enums.payment import PaymentMethod


async def getter_select_method(
    dialog_manager: DialogManager,
    **kwargs,
) -> dict:
    amount = dialog_manager.dialog_data["amount"]

    methods = [
        {"id": PaymentMethod.TELEGRAM_STARS.value, "title": "💫 Telegram Stars"},
        # {"id": PaymentMethod.MANUAL_CARD.value, "title": "💳 Перевод на карту"},
        {"id": PaymentMethod.YOOKASSA.value, "title": "🏦 ЮKassa"},
        # {"id": PaymentMethod.CRYPTO.value, "title": "₿ Криптовалюта"},  # пока не готово
    ]

    return {"amount": amount, "methods": methods}
