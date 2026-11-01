from datetime import date, datetime, timezone
from decimal import Decimal
from io import BytesIO

from openpyxl import load_workbook

from src.application.dtos.stats_report import (
    ColumnKind,
    ReportColumn,
    ReportSheet,
    ReportWorkbook,
)
from src.infrastructure.reports.xlsx_writer import OpenpyxlReportWriter


def _render(sheets, params=None):
    workbook = ReportWorkbook(params=params or [("Период", "Месяц")], sheets=sheets)
    return load_workbook(BytesIO(OpenpyxlReportWriter().render(workbook)))


def _sheet(kind, value, title="Лист"):
    return ReportSheet(
        title=title,
        columns=(ReportColumn("v", "Значение", kind),),
        rows=[{"v": value}],
    )


def test_params_sheet_comes_first():
    book = _render([_sheet(ColumnKind.TEXT, "x")])
    assert book.sheetnames == ["Параметры", "Лист"]
    assert book["Параметры"]["A1"].value == "Период"
    assert book["Параметры"]["B1"].value == "Месяц"


def test_user_text_never_becomes_formula():
    """Имя пользователя с «=...» не должно выполниться в Excel у админа."""
    evil = '=HYPERLINK("http://evil","x")'
    book = _render([_sheet(ColumnKind.TEXT, evil)])
    cell = book["Лист"]["A2"]
    assert cell.value == evil
    assert cell.data_type != "f"


def test_control_characters_do_not_break_the_file():
    book = _render([_sheet(ColumnKind.TEXT, "Ив\x00ан\x1f🚗")])
    assert book["Лист"]["A2"].value == "Иван🚗"


def test_text_longer_than_excel_cell_is_cut():
    book = _render([_sheet(ColumnKind.TEXT, "я" * 40_000)])
    assert len(book["Лист"]["A2"].value) == 32_767


def test_money_stays_a_number():
    book = _render([_sheet(ColumnKind.MONEY, Decimal("1234.50"))])
    cell = book["Лист"]["A2"]
    assert cell.value == 1234.5
    assert cell.number_format == "#,##0.00"


def test_aware_datetime_is_written_in_moscow_time():
    moment = datetime(2026, 10, 1, 21, 30, tzinfo=timezone.utc)
    book = _render([_sheet(ColumnKind.DATETIME, moment)])
    assert book["Лист"]["A2"].value == datetime(2026, 10, 2, 0, 30)


def test_date_and_bool_and_none():
    columns = (
        ReportColumn("d", "Дата", ColumnKind.DATE),
        ReportColumn("yes", "Да", ColumnKind.BOOL),
        ReportColumn("no", "Нет", ColumnKind.BOOL),
        ReportColumn("empty", "Пусто", ColumnKind.MONEY),
    )
    rows = [{"d": date(2026, 10, 2), "yes": True, "no": False, "empty": None}]
    ws = _render([ReportSheet("Лист", columns, rows)])["Лист"]
    assert ws["A2"].value.date() == date(2026, 10, 2)
    assert (ws["B2"].value, ws["C2"].value, ws["D2"].value) == ("да", "нет", None)


def test_header_filter_and_freeze():
    ws = _render([_sheet(ColumnKind.INT, 1)])["Лист"]
    assert ws["A1"].value == "Значение"
    assert ws["A1"].font.bold
    assert ws.freeze_panes == "A2"
    assert ws.auto_filter.ref == "A1:A2"


def test_empty_sheet_keeps_header():
    sheet = ReportSheet("Лист", (ReportColumn("v", "Значение"),), [])
    ws = _render([sheet])["Лист"]
    assert ws["A1"].value == "Значение"
    assert ws.max_row == 1


def test_sheet_titles_are_valid_and_unique():
    long = "Очень длинное название раздела: больше/тридцати*одного"
    book = _render([_sheet(ColumnKind.INT, 1, long), _sheet(ColumnKind.INT, 2, long)])
    first, second = book.sheetnames[1:]
    assert first != second
    assert all(len(t) <= 31 for t in (first, second))
    assert not set("[]:*?/\\") & set(first + second)
