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
        {"id": PaymentMethod.MANUAL_CARD.value, "title": "💳 Перевод на карту"},
    ]

    return {"amount": amount, "description": description, "methods": methods}