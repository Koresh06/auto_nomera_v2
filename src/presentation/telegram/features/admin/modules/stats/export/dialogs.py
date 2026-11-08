from aiogram import F
from aiogram.enums import ButtonStyle
from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import (
    Button,
    Cancel,
    Multiselect,
    Row,
    ScrollingGroup,
    SwitchTo,
)
from aiogram_dialog.widgets.style import Style
from aiogram_dialog.widgets.text import Const, Format

from src.domain.value_objects.date_range import DateRange

from .getters import (
    getter_export_menu,
    getter_export_period,
    getter_export_preview,
    getter_export_regions,
    getter_export_sections,
)
from .handlers import (
    on_all_regions,
    on_dates_entered,
    on_dates_invalid,
    on_download,
    on_export_start,
    on_preset_selected,
    on_preview,
)
from .selection import REGIONS_WIDGET, SECTIONS_WIDGET
from .states import StatsExportSG


def _to_menu(text: str = "⬅️ Назад") -> SwitchTo:
    return SwitchTo(
        Const(text),
        id="to_export_menu",
        state=StatsExportSG.menu,
        style=Style(style=ButtonStyle.PRIMARY),
    )


stats_export_dialog = Dialog(
    Window(
        Format(
            "📤 <b>Выгрузка статистики</b>\n\n"
            "📅 Период: <b>{period_label}</b>\n"
            "📍 Регионы: <b>{regions_label}</b>\n"
            "📑 Разделы: <b>{sections_label}</b>\n\n"
            "Настройте отчёт, посмотрите итоги или скачайте Excel: "
            "каждый раздел будет отдельным листом."
        ),
        Const(
            "\n🔒 Контакты и балансы пользователей в файл не попадут.",
            when=F["personal_hidden"],
        ),
        SwitchTo(Const("📅 Период"), id="to_period", state=StatsExportSG.period),
        Row(
            SwitchTo(Const("📍 Регионы"), id="to_regions", state=StatsExportSG.regions),
            SwitchTo(
                Const("📑 Разделы"), id="to_sections", state=StatsExportSG.sections
            ),
        ),
        Button(Const("👀 Посмотреть итоги"), id="preview", on_click=on_preview),
        Button(Const("📥 Скачать Excel"), id="download", on_click=on_download),
        Cancel(Const("⬅️ Назад"), style=Style(style=ButtonStyle.PRIMARY)),
        state=StatsExportSG.menu,
        getter=getter_export_menu,
    ),
    Window(
        Const("📅 <b>Выберите период:</b>"),
        Row(
            Button(Format("{lbl_today}"), id="today", on_click=on_preset_selected),
            Button(Format("{lbl_week}"), id="week", on_click=on_preset_selected),
        ),
        Row(
            Button(Format("{lbl_month}"), id="month", on_click=on_preset_selected),
            Button(Format("{lbl_all}"), id="all", on_click=on_preset_selected),
        ),
        SwitchTo(
            Format("{lbl_custom}"), id="to_dates", state=StatsExportSG.custom_dates
        ),
        _to_menu(),
        state=StatsExportSG.period,
        getter=getter_export_period,
    ),
    Window(
        Const(
            "📆 <b>Введите период</b>\n\n"
            "Одной строкой, по московскому времени:\n"
            "<code>01.10.2026 - 31.10.2026</code>\n\n"
            "Для одного дня достаточно одной даты."
        ),
        TextInput(
            id="export_dates",
            type_factory=DateRange.parse,
            on_success=on_dates_entered,
            on_error=on_dates_invalid,
        ),
        SwitchTo(Const("⬅️ Назад"), id="dates_back", state=StatsExportSG.period),
        state=StatsExportSG.custom_dates,
    ),
    Window(
        Const("📍 <b>Выберите регионы</b>\n\nНичего не отмечено — все регионы."),
        ScrollingGroup(
            Multiselect(
                Format("✅ {item.title}"),
                Format("▫️ {item.title}"),
                id=REGIONS_WIDGET,
                items="regions",
                item_id_getter=lambda item: item.id,
            ),
            id="export_regions_scroll",
            width=1,
            height=10,
            hide_on_single_page=True,
        ),
        Button(Const("🌍 Все регионы"), id="all_regions", on_click=on_all_regions),
        _to_menu("✅ Готово"),
        state=StatsExportSG.regions,
        getter=getter_export_regions,
    ),
    Window(
        Const("📑 <b>Выберите разделы</b>"),
        ScrollingGroup(
            Multiselect(
                Format("✅ {item[title]}"),
                Format("▫️ {item[title]}"),
                id=SECTIONS_WIDGET,
                items="sections",
                item_id_getter=lambda item: item["id"],
            ),
            id="export_sections_scroll",
            width=1,
            height=10,
            hide_on_single_page=True,
        ),
        _to_menu("✅ Готово"),
        state=StatsExportSG.sections,
        getter=getter_export_sections,
    ),
    Window(
        Format(
            "👀 <b>Итоги: {period_label}</b>\n\n"
            "💰 <b>Выручка: {revenue} руб.</b>\n"
            "  Покупок: <b>{purchases}</b>\n"
            "  Слоты: <b>{revenue_slot}</b>\n"
            "  Услуги: <b>{revenue_service}</b>\n"
            "  Подписка: <b>{revenue_pre}</b>\n"
            "  Из них с баланса: <b>{from_balance}</b>\n\n"
            "💵 <b>Поступило: {inflow} руб.</b>\n"
            "  Из них пополнения: <b>{topups}</b>\n\n"
            "👥 Новых пользователей: <b>{users_new}</b> (всего {users_total})\n"
            "📣 Новых объявлений: <b>{ads_new}</b>\n"
            "📦 Публикаций: <b>{publications}</b>\n"
            "💎 Подключено услуг: <b>{services}</b>\n"
            "{row_lines}"
        ),
        Button(Const("📥 Скачать Excel"), id="download", on_click=on_download),
        _to_menu(),
        state=StatsExportSG.preview,
        getter=getter_export_preview,
    ),
    on_start=on_export_start,
)
