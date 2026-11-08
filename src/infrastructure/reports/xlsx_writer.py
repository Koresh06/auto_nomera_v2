from datetime import datetime
from io import BytesIO
from typing import Any

from openpyxl import Workbook
from openpyxl.cell import WriteOnlyCell
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from src.application.dtos.stats_report import (
    ColumnKind,
    ReportColumn,
    ReportSheet,
    ReportWorkbook,
)
from src.domain.enums.period import MSK

_EXCEL_CELL_LIMIT = 32_767
_HEADER_FONT = Font(bold=True, color="FFFFFF")
_HEADER_FILL = PatternFill("solid", fgColor="2F5597")
_FORMATS = {
    ColumnKind.MONEY: "#,##0.00",
    ColumnKind.INT: "0",
    ColumnKind.DATETIME: "DD.MM.YYYY HH:MM",
    ColumnKind.DATE: "DD.MM.YYYY",
}
_WIDTHS = {
    ColumnKind.TEXT: 22,
    ColumnKind.INT: 12,
    ColumnKind.MONEY: 15,
    ColumnKind.DATETIME: 18,
    ColumnKind.DATE: 13,
    ColumnKind.BOOL: 12,
}


class OpenpyxlReportWriter:
    def render(self, workbook: ReportWorkbook) -> bytes:
        # write_only: выгрузка всех пользователей не держит в памяти объект
        # на каждую ячейку
        book = Workbook(write_only=True)
        self._write_params(book, workbook.params)
        used: set[str] = set()
        for sheet in workbook.sheets:
            self._write_sheet(book, sheet, used)
        buffer = BytesIO()
        book.save(buffer)
        return buffer.getvalue()

    def _write_params(self, book: Workbook, params: list[tuple[str, str]]) -> None:
        ws = book.create_sheet("Параметры")
        ws.column_dimensions["A"].width = 24
        ws.column_dimensions["B"].width = 90
        for name, value in params:
            label = self._text_cell(ws, name)
            label.font = Font(bold=True)
            ws.append([label, self._text_cell(ws, value)])

    def _write_sheet(self, book: Workbook, sheet: ReportSheet, used: set[str]) -> None:
        ws = book.create_sheet(self._sheet_title(sheet.title, used))
        ws.freeze_panes = "A2"
        for index, column in enumerate(sheet.columns, start=1):
            width = _WIDTHS[column.kind]
            ws.column_dimensions[get_column_letter(index)].width = width
        if sheet.columns:
            last = get_column_letter(len(sheet.columns))
            ws.auto_filter.ref = f"A1:{last}{len(sheet.rows) + 1}"

        ws.append([self._header_cell(ws, c.title) for c in sheet.columns])
        for row in sheet.rows:
            ws.append([self._cell(ws, c, row.get(c.key)) for c in sheet.columns])

    @staticmethod
    def _sheet_title(title: str, used: set[str]) -> str:
        cleaned = title.translate({ord(c): " " for c in "[]:*?/\\"})[:31]
        result = cleaned
        suffix = 2
        while result in used:
            result = f"{cleaned[:28]} {suffix}"
            suffix += 1
        used.add(result)
        return result

    def _header_cell(self, ws: Worksheet, title: str) -> WriteOnlyCell:
        cell = self._text_cell(ws, title)
        cell.font = _HEADER_FONT
        cell.fill = _HEADER_FILL
        cell.alignment = Alignment(wrap_text=True, vertical="center")
        return cell

    def _cell(self, ws: Worksheet, column: ReportColumn, value: Any) -> WriteOnlyCell:
        if value is None:
            return WriteOnlyCell(ws, value=None)
        if column.kind == ColumnKind.BOOL:
            return self._text_cell(ws, "да" if value else "нет")
        if column.kind == ColumnKind.TEXT:
            return self._text_cell(ws, str(value))

        if isinstance(value, datetime) and value.tzinfo is not None:
            # Excel не знает таймзон, а openpyxl на aware-datetime падает
            value = value.astimezone(MSK).replace(tzinfo=None)
        cell = WriteOnlyCell(ws, value=value)
        cell.number_format = _FORMATS[column.kind]
        return cell

    @staticmethod
    def _text_cell(ws: Worksheet, value: str) -> WriteOnlyCell:
        cleaned = ILLEGAL_CHARACTERS_RE.sub("", value)[:_EXCEL_CELL_LIMIT]
        cell = WriteOnlyCell(ws, value=cleaned)
        # Имена и названия вводят пользователи. «=HYPERLINK(...)» без этого
        # стал бы формулой и выполнился у админа при открытии файла.
        cell.data_type = "s"
        return cell
