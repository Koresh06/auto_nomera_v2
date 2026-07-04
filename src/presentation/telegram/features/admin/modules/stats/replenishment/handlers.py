from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, ShowMode
from aiogram_dialog.widgets.kbd import Button, Select

from src.domain.enums.period import StatsPeriod
from src.presentation.telegram.features.admin.modules.stats.replenishment.states import (
    StatsReplenishmentSG,
)


async def on_period_selected(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
) -> None:
    state = dialog_manager.current_context().state
    if state == StatsReplenishmentSG.general:
        dialog_manager.dialog_data["period_general"] = button.widget_id
    else:
        dialog_manager.dialog_data["period_region"] = button.widget_id
    await dialog_manager.show(show_mode=ShowMode.EDIT)


async def on_region_selected(
    callback: CallbackQuery,
    widget: Select,
    dialog_manager: DialogManager,
    item_id: str,
) -> None:
    dialog_manager.dialog_data["region_id"] = int(item_id)
    dialog_manager.dialog_data["period"] = StatsPeriod.MONTH.value
    await dialog_manager.next()
