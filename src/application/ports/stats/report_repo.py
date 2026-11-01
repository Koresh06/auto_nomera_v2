from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any, Protocol

from src.application.dtos.stats_report import RegionMetrics, ReportFilter
from src.domain.enums.report import ReportSection


class StatsReportRepository(Protocol):
    async def get_region_metrics(self, report_filter: ReportFilter) -> RegionMetrics:
        """Показатели по регионам: ключи описаны в stats_report.sections.
        Сводка считается как сумма этих строк, поэтому листы всегда сходятся."""
        ...

    async def fetch_rows(
        self, section: ReportSection, report_filter: ReportFilter
    ) -> Sequence[Mapping[str, Any]]: ...

    async def count_rows(
        self, section: ReportSection, report_filter: ReportFilter
    ) -> int: ...

    async def ledger_started_at(self) -> datetime | None: ...
