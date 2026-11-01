from typing import Protocol

from src.application.dtos.stats_report import ReportWorkbook


class ReportWriter(Protocol):
    def render(self, workbook: ReportWorkbook) -> bytes:
        """Синхронный и CPU-ёмкий: вызывать вне event loop."""
        ...
