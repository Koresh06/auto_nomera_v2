from decimal import Decimal, InvalidOperation
from datetime import time

from dishka.integrations.aiogram_dialog import inject, FromDishka
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager, ShowMode
from aiogram_dialog.widgets.kbd import Button
from aiogram_dialog.widgets.input import ManagedTextInput

from src.application.mediator import Mediator
from src.application.use_cases.region.update_settings import UpdateRegionSettingsCommand
from src.domain.value_objects.region_settings import RegionSettings
from src.presentation.telegram.features.admin.modules.region.edit.states import EditRegionSettingsSG



def _parse_field(widget_id: str, raw: str) -> tuple[str, object]:
    value = raw.strip()

    if widget_id == "days_range_input":
        days = int(value)
        if days < 1 or days > 31:
            raise ValueError("Введите число от 1 до 31")
        return "days_range", days

    if widget_id == "paid_count_input":
        count = int(value)
        if count < 0:
            raise ValueError("Введите неотрицательное целое число")
        return "system_paid_slots_count", count

    if widget_id == "price_input":
        price = Decimal(value.replace(",", "."))
        if price < 0:
            raise ValueError("Цена не может быть отрицательной")
        return "paid_slot_price", price

    raise ValueError("Неизвестное поле")


@inject
async def on_settings_field_update(
    message: Message,
    widget: ManagedTextInput,
    dialog_manager: DialogManager,
    value: str,
    mediator: FromDishka[Mediator],
) -> None:
    region_id: int = dialog_manager.start_data["region_id"]

    try:
        field, parsed = _parse_field(widget.widget.widget_id, value)
    except (ValueError, InvalidOperation) as e:
        text = str(e)
        if not text or "invalid literal" in text or "ConversionSyntax" in text:
            text = "Введите корректное значение"
        await message.answer(f"⚠️ {text}")
        return

    try:
        await mediator.handle(
            UpdateRegionSettingsCommand(region_id=region_id, **{field: parsed})
        )
    except Exception as e:
        await message.answer(f"⚠️ {e}")
        return

    await message.answer("✅ Сохранено")
    await dialog_manager.switch_to(EditRegionSettingsSG.menu)


@inject
async def on_toggle_publication_limit(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
) -> None:
    region_id: int = dialog_manager.start_data["region_id"]
    current = dialog_manager.dialog_data.get("publication_limit_enabled", False)
    new_value = not current

    await mediator.handle(
        UpdateRegionSettingsCommand(
            region_id=region_id,
            publication_limit_enabled=new_value,
        )
    )
    dialog_manager.dialog_data["publication_limit_enabled"] = new_value
    await callback.answer(
        f"Лимит публикаций: {'включён' if new_value else 'выключен'}"
    )
    await dialog_manager.show(show_mode=ShowMode.EDIT)


async def on_slot_time_toggle(
    callback: CallbackQuery,
    widget,
    dialog_manager: DialogManager,
    item_id: str,
) -> None:
    selected: list[str] = dialog_manager.dialog_data.setdefault("slot_times", [])
    if item_id in selected:
        selected.remove(item_id)
    else:
        selected.append(item_id)
        selected.sort()


@inject
async def on_slot_times_done(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
) -> None:
    selected: list[str] = dialog_manager.dialog_data.get("slot_times", [])
    if not selected:
        await callback.answer("⚠️ Выберите хотя бы одно время", show_alert=True)
        return

    region_id: int = dialog_manager.start_data["region_id"]
    slot_times = tuple(time.fromisoformat(t) for t in selected)

    try:
        await mediator.handle(
            UpdateRegionSettingsCommand(region_id=region_id, slot_times=slot_times)
        )
    except Exception as e:
        await callback.answer(f"⚠️ {e}", show_alert=True)
        return

    await callback.answer("✅ Времена сохранены")
    await dialog_manager.switch_to(EditRegionSettingsSG.menu)


@inject
async def on_reset_defaults(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
) -> None:
    data = dialog_manager.dialog_data

    if not data.get("reset_confirm_pending"):
        data["reset_confirm_pending"] = True
        await callback.answer(
            "⚠️ Сбросить к стандартным значениям? Нажмите ещё раз для подтверждения",
            show_alert=True,
        )
        return

    data["reset_confirm_pending"] = False
    region_id: int = dialog_manager.start_data["region_id"]
    defaults = RegionSettings()

    await mediator.handle(
        UpdateRegionSettingsCommand(
            region_id=region_id,
            slot_times=defaults.slot_times,
            days_range=defaults.days_range,
            system_paid_slots_count=defaults.system_paid_slots_count,
            publication_limit_enabled=defaults.publication_limit_enabled,
            paid_slot_price=defaults.paid_slot_price,
        )
    )
    await callback.answer("♻️ Значения сброшены к стандартным")
    await dialog_manager.show(show_mode=ShowMode.EDIT)