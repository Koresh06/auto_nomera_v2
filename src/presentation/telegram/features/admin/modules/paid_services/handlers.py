from dishka.integrations.aiogram_dialog import inject, FromDishka
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager, ShowMode
from aiogram_dialog.widgets.kbd import Button
from aiogram_dialog.widgets.input import ManagedTextInput

from src.application.dtos.service_definition import ServiceDefinitionDTO
from src.application.mediator import Mediator
from src.application.use_cases.service_difinition.get_by_id import (
    GetByIdServiceDefinitionRequest,
)
from src.application.use_cases.service_difinition.toggle_status import (
    ToggleServiceStatusCommand,
)
from src.application.use_cases.service_difinition.update import UpdateServiceCommand
from src.infrastructure.seeds.service_definitions import DEFAULT_SERVICES_BY_TYPE

from .states import (
    PaidServiceAdminSG,
)


async def on_service_selected(
    callback: CallbackQuery,
    widget,
    dialog_manager: DialogManager,
    item_id: str,
) -> None:
    dialog_manager.dialog_data["service_id"] = int(item_id)
    await dialog_manager.switch_to(PaidServiceAdminSG.detail)


@inject
async def on_toggle_status(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
) -> None:
    service_id: int = dialog_manager.dialog_data["service_id"]

    if not dialog_manager.dialog_data.get("toggle_confirm_pending"):
        dialog_manager.dialog_data["toggle_confirm_pending"] = True
        await callback.answer(
            "⚠️ Нажмите ещё раз, чтобы подтвердить смену статуса",
            show_alert=True,
        )
        await dialog_manager.show(show_mode=ShowMode.EDIT)
        return

    dialog_manager.dialog_data["toggle_confirm_pending"] = False
    await mediator.handle(ToggleServiceStatusCommand(service_id=service_id))
    await callback.answer("✅ Статус изменён")
    await dialog_manager.show(show_mode=ShowMode.EDIT)


def _parse_field(widget_id: str, raw: str) -> tuple[str, object]:
    """Возвращает (имя_поля_команды, значение) или бросает ValueError с текстом ошибки."""
    value = raw.strip()

    if widget_id == "price_input":
        price = int(value)
        if price < 0:
            raise ValueError("Введите целое неотрицательное число")
        return "price", price

    if widget_id == "duration_input":
        days = int(value)
        if days <= 0:
            raise ValueError("Введите положительное целое число")
        return "duration_days", days

    if widget_id == "title_input":
        if not value:
            raise ValueError("Название не может быть пустым")
        return "title", value

    if widget_id == "description_input":
        return "description", None if value == "-" else value

    raise ValueError("Неизвестное поле")


@inject
async def on_field_update(
    message: Message,
    widget: ManagedTextInput,
    dialog_manager: DialogManager,
    value: str,
    mediator: FromDishka[Mediator],
) -> None:
    try:
        field, parsed = _parse_field(widget.widget.widget_id, value)
    except ValueError as e:
        text = str(e) if str(e) and "invalid literal" not in str(e) else "Введите число"
        await message.answer(f"⚠️ {text}")
        return

    service_id: int = dialog_manager.dialog_data["service_id"]
    await mediator.handle(
        UpdateServiceCommand(service_id=service_id, **{field: parsed})
    )
    await message.answer("✅ Изменения сохранены")
    await dialog_manager.switch_to(PaidServiceAdminSG.detail)


@inject
async def on_reset_default(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
) -> None:
    if not dialog_manager.dialog_data.get("reset_confirm_pending"):
        dialog_manager.dialog_data["reset_confirm_pending"] = True
        await callback.answer(
            "⚠️ Сбросить к стандартным значениям? Нажмите ещё раз для подтверждения",
            show_alert=True,
        )
        return

    dialog_manager.dialog_data["reset_confirm_pending"] = False
    service_id: int = dialog_manager.dialog_data["service_id"]

    service: ServiceDefinitionDTO = await mediator.handle(
        GetByIdServiceDefinitionRequest(id=service_id)
    )
    default = DEFAULT_SERVICES_BY_TYPE.get(service.type)
    if default is None:
        await callback.answer("⚠️ Нет дефолта для этой услуги", show_alert=True)
        return

    await mediator.handle(
        UpdateServiceCommand(
            service_id=service_id,
            title=default["title"],
            price=default["price"],
            duration_days=default["duration_days"],
            description=default["description"],
        )
    )
    await callback.answer("♻️ Услуга сброшена к стандартным значениям")
