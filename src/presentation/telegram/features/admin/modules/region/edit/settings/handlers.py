from datetime import time
from decimal import Decimal, InvalidOperation

from dishka.integrations.aiogram_dialog import inject, FromDishka
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Button

from src.application.mediator import Mediator
from src.application.use_cases.region.update_settings import UpdateRegionSettingsCommand
from src.domain.value_objects.region_settings import RegionSettings
from src.presentation.telegram.features.admin.modules.region.edit.states import EditRegionSettingsSG



async def on_toggle_publication_limit(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
) -> None:
    current = dialog_manager.dialog_data["publication_limit_enabled"]
    dialog_manager.dialog_data["publication_limit_enabled"] = not current
    await callback.answer(
        f"Лимит публикаций: {'включён' if not current else 'выключен'}"
    )


async def on_slot_time_toggle(
    callback: CallbackQuery,
    widget,
    dialog_manager: DialogManager,
    item_id: str,
) -> None:
    selected: list[str] = dialog_manager.dialog_data.get("slot_times", [])

    if item_id in selected:
        selected.remove(item_id)
    else:
        selected.append(item_id)
        selected.sort()

    dialog_manager.dialog_data["slot_times"] = selected


async def on_slot_times_done(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
) -> None:
    if not dialog_manager.dialog_data.get("slot_times"):
        await callback.answer("⚠️ Выберите хотя бы одно время", show_alert=True)
        return
    await dialog_manager.switch_to(EditRegionSettingsSG.menu)


async def on_days_range_success(
    message: Message,
    widget,
    dialog_manager: DialogManager,
    value: int,
) -> None:
    try:
        if value < 1 or value > 31:
            raise ValueError
    except ValueError:
        await message.answer("⚠️ Введите число от 1 до 31")
        return

    dialog_manager.dialog_data["days_range"] = value
    await dialog_manager.switch_to(EditRegionSettingsSG.menu)


async def on_system_paid_count_success(
    message: Message,
    widget,
    dialog_manager: DialogManager,
    value: int,
) -> None:
    try:
        if value < 0:
            raise ValueError
    except ValueError:
        await message.answer("⚠️ Введите неотрицательное целое число")
        return

    dialog_manager.dialog_data["system_paid_slots_count"] = value
    await dialog_manager.switch_to(EditRegionSettingsSG.menu)


async def on_paid_slot_price_success(
    message: Message,
    widget,
    dialog_manager: DialogManager,
    value: float,
) -> None:
    try:
        price = Decimal(value)
        if price < 0:
            raise ValueError
    except (InvalidOperation, ValueError):
        await message.answer("⚠️ Введите корректную сумму (например: 2.50)")
        return

    dialog_manager.dialog_data["paid_slot_price"] = str(price)
    await dialog_manager.switch_to(EditRegionSettingsSG.menu)


async def on_reset_defaults(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
) -> None:
    defaults = RegionSettings()
    data = dialog_manager.dialog_data

    data["slot_times"] = [t.strftime("%H:%M") for t in defaults.slot_times]
    data["days_range"] = defaults.days_range
    data["system_paid_slots_count"] = defaults.system_paid_slots_count
    data["publication_limit_enabled"] = defaults.publication_limit_enabled
    data["paid_slot_price"] = str(defaults.paid_slot_price)

    await callback.answer("♻️ Значения сброшены к стандартным. Нажмите 'Сохранить'")


@inject
async def on_settings_confirm(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
) -> None:
    data = dialog_manager.dialog_data

    slot_times = tuple(
        time.fromisoformat(t) for t in data["slot_times"]
    )
    days_range = data["days_range"]
    system_paid = data["system_paid_slots_count"]

    total_slots = days_range * len(slot_times)
    if system_paid > total_slots:
        await callback.answer(
            f"⚠️ Платных слотов ({system_paid}) больше, чем всего слотов ({total_slots}). "
            f"Уменьшите количество или добавьте времена.",
            show_alert=True,
        )
        return

    await mediator.handle(
        UpdateRegionSettingsCommand(
            region_id=data["region_id"],
            slot_times=slot_times,
            days_range=days_range,
            system_paid_slots_count=system_paid,
            publication_limit_enabled=data["publication_limit_enabled"],
            paid_slot_price=Decimal(data["paid_slot_price"]),
        )
    )
    await callback.answer("✅ Настройки сохранены")
    await dialog_manager.done()