from aiogram_dialog import DialogManager
from src.domain.enums.payment import PaymentMethod


async def getter_select_payment_method(
    dialog_manager: DialogManager,
    **kwargs,
) -> dict:
    start_data = dialog_manager.start_data
    amount = start_data["amount"]
    description = start_data.get("description", "")

    methods = [
        {"id": PaymentMethod.TELEGRAM_STARS.value, "title": "💫 Telegram Stars"},
        # {"id": PaymentMethod.MANUAL_CARD.value, "title": "💳 Перевод на карту"},
        {"id": PaymentMethod.YOOKASSA.value, "title": "🏦 ЮKassa"},
        # {"id": PaymentMethod.CRYPTO.value, "title": "₿ Криптовалюта"},  # пока не готово
    ]

    return {"amount": amount, "description": description, "methods": methods}
