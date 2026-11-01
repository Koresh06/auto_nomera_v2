import logging

from aiogram.types import BufferedInputFile, CallbackQuery, Message
from aiogram_dialog import DialogManager, ShowMode
from aiogram_dialog.widgets.input import ManagedTextInput
from aiogram_dialog.widgets.kbd import Button
from dishka.integrations.aiogram_dialog import FromDishka, inject

from src.application.dtos.stats_report import ReportFile
from src.application.mediator import Mediator
from src.application.use_cases.stats.report import BuildStatsReportRequest
from src.core.config import settings
from src.domain.enums.period import StatsPeriod
from src.domain.value_objects.date_range import DateRange

from .selection import (
    CUSTOM_PERIOD,
    DEFAULT_SECTIONS,
    REGIONS_WIDGET,
    SECTIONS_WIDGET,
    period_label,
    report_filter,
    selected_sections,
)
from .states import StatsExportSG

logger = logging.getLogger(__name__)

# лимит Bot API на sendDocument
MAX_FILE_BYTES = 50 * 1024 * 1024
# Сборка файла занимает секунды: второе нажатие не должно запускать её ещё раз.
_exports_in_progress: set[int] = set()


async def on_export_start(start_data: object, manager: DialogManager) -> None:
    widget = manager.find(SECTIONS_WIDGET)
    for section in DEFAULT_SECTIONS:
        await widget.set_checked(section.value, True)


async def on_preset_selected(
    callback: CallbackQuery, button: Button, manager: DialogManager
) -> None:
    manager.dialog_data["period"] = StatsPeriod(button.widget_id).value
    await manager.switch_to(StatsExportSG.menu)


async def on_dates_entered(
    message: Message,
    widget: ManagedTextInput,
    manager: DialogManager,
    value: DateRange,
) -> None:
    manager.dialog_data.update(
        period=CUSTOM_PERIOD,
        date_from=value.start.isoformat(),
        date_to=value.end.isoformat(),
    )
    await manager.switch_to(StatsExportSG.menu)


async def on_dates_invalid(
    message: Message,
    widget: ManagedTextInput,
    manager: DialogManager,
    error: ValueError,
) -> None:
    await message.answer(f"⚠️ {error}. Пример: 01.10.2026 - 31.10.2026")


async def on_all_regions(
    callback: CallbackQuery, button: Button, manager: DialogManager
) -> None:
    await manager.find(REGIONS_WIDGET).reset_checked()
    await manager.switch_to(StatsExportSG.menu)


async def on_preview(
    callback: CallbackQuery, button: Button, manager: DialogManager
) -> None:
    if not selected_sections(manager):
        await callback.answer("Выберите хотя бы один раздел", show_alert=True)
        return
    await manager.switch_to(StatsExportSG.preview)


@inject
async def on_download(
    callback: CallbackQuery,
    button: Button,
    manager: DialogManager,
    mediator: FromDishka[Mediator],
) -> None:
    sections = selected_sections(manager)
    if not sections:
        await callback.answer("Выберите хотя бы один раздел", show_alert=True)
        return

    tg_id = callback.from_user.id
    if tg_id in _exports_in_progress:
        await callback.answer("⏳ Файл уже готовится")
        return

    _exports_in_progress.add(tg_id)
    try:
        await callback.answer("⏳ Готовлю файл…")
        # Права проверяются здесь, на сервере, по конфигу: диалог могут
        # открыть и назначенные админы, а им персональные данные не положены.
        report: ReportFile = await mediator.handle(
            BuildStatsReportRequest(
                report_filter=report_filter(manager),
                sections=sections,
                period_label=period_label(manager),
                include_personal=tg_id in settings.telegram.admin_ids,
            )
        )
        if len(report.content) > MAX_FILE_BYTES:
            await callback.message.answer(
                "⚠️ Файл больше 50 МБ — Telegram его не примет. "
                "Сократите период или число разделов."
            )
        else:
            await callback.message.answer_document(
                BufferedInputFile(report.content, filename=report.filename),
                caption=f"📊 Статистика: {period_label(manager)}",
            )
    finally:
        _exports_in_progress.discard(tg_id)

    # файл должен остаться в чате выше окна диалога
    manager.show_mode = ShowMode.DELETE_AND_SEND
