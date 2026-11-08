import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from src.application.dtos.stats_report import (
    Metrics,
    ReportFile,
    ReportFilter,
    ReportPreviewDTO,
    ReportSheet,
    ReportWorkbook,
    sum_metrics,
)
from src.application.ports.region.region_repo import RegionRepository
from src.application.ports.stats.report_repo import StatsReportRepository
from src.application.ports.stats.report_writer import ReportWriter
from src.application.services.stats_report.sections import (
    METRIC_COLUMNS,
    SECTIONS,
)
from src.application.use_cases.base import UseCase, UseCaseRequest
from src.domain.enums.period import MSK
from src.domain.enums.report import ReportSection

logger = logging.getLogger(__name__)

NO_REGION = "Без региона"
_DETAIL_SECTIONS = (ReportSection.SUMMARY, ReportSection.REGIONS)


@dataclass(frozen=True, eq=False)
class GetReportPreviewRequest(UseCaseRequest):
    report_filter: ReportFilter
    sections: tuple[ReportSection, ...]


@dataclass(kw_only=True)
class GetReportPreviewUseCase(UseCase[GetReportPreviewRequest, ReportPreviewDTO]):
    report_repo: StatsReportRepository

    async def __call__(self, command: GetReportPreviewRequest) -> ReportPreviewDTO:
        metrics = await self.report_repo.get_region_metrics(command.report_filter)
        counts = {
            section: await self.report_repo.count_rows(section, command.report_filter)
            for section in command.sections
            if section not in _DETAIL_SECTIONS
        }
        return ReportPreviewDTO(totals=sum_metrics(metrics.values()), row_counts=counts)


@dataclass(frozen=True, eq=False)
class BuildStatsReportRequest(UseCaseRequest):
    report_filter: ReportFilter
    sections: tuple[ReportSection, ...]
    period_label: str
    # без явного True персональные колонки не попадают в файл
    include_personal: bool = False


@dataclass(kw_only=True)
class BuildStatsReportUseCase(UseCase[BuildStatsReportRequest, ReportFile]):
    report_repo: StatsReportRepository
    region_repo: RegionRepository
    writer: ReportWriter

    async def __call__(self, command: BuildStatsReportRequest) -> ReportFile:
        if not command.sections:
            raise ValueError("Не выбрано ни одного раздела")

        flt = command.report_filter
        titles = {r.id: r.title for r in await self.region_repo.get_all()}

        sheets: list[ReportSheet] = []
        for section in command.sections:
            sheets.append(
                await self._sheet(section, flt, titles, command.include_personal)
            )

        now = datetime.now(timezone.utc)
        workbook = ReportWorkbook(
            params=await self._params(command, titles, now), sheets=sheets
        )
        content = await asyncio.to_thread(self.writer.render, workbook)

        logger.info(
            f"[BuildStatsReport] sections={[s.value for s in command.sections]} "
            f"regions={flt.region_ids} personal={command.include_personal} "
            f"bytes={len(content)}"
        )
        return ReportFile(
            filename=f"stats_{now.astimezone(MSK):%Y-%m-%d_%H%M}.xlsx",
            content=content,
        )

    async def _sheet(
        self,
        section: ReportSection,
        flt: ReportFilter,
        titles: dict[int, str],
        include_personal: bool,
    ) -> ReportSheet:
        definition = SECTIONS[section]
        columns = tuple(
            c for c in definition.columns if include_personal or not c.personal
        )

        rows: list[dict[str, Any]]
        if section == ReportSection.SUMMARY:
            metrics = await self.report_repo.get_region_metrics(flt)
            rows = _summary_rows(sum_metrics(metrics.values()))
        elif section == ReportSection.REGIONS:
            metrics = await self.report_repo.get_region_metrics(flt)
            rows = _region_rows(metrics, titles)
        else:
            raw = await self.report_repo.fetch_rows(section, flt)
            # только выбранные колонки: персональные значения не должны
            # доходить до writer'а даже в словаре строки
            rows = [_project(row, columns) for row in raw]

        return ReportSheet(title=definition.title, columns=columns, rows=rows)

    async def _params(
        self,
        command: BuildStatsReportRequest,
        titles: dict[int, str],
        now: datetime,
    ) -> list[tuple[str, str]]:
        region_ids = command.report_filter.region_ids
        regions = (
            ", ".join(titles.get(rid, f"#{rid}") for rid in region_ids)
            if region_ids
            else "Все регионы"
        )
        started = await self.report_repo.ledger_started_at()
        ledger_note = (
            f"Покупки с баланса учтены с {started.astimezone(MSK):%d.%m.%Y %H:%M} МСК: "
            "более ранние списания в базе не сохранялись"
            if started
            else "Покупок с баланса пока не было: журнал ведётся с этой версии бота"
        )
        return [
            ("Период", command.period_label),
            ("Регионы", regions),
            ("Сформирован", f"{now.astimezone(MSK):%d.%m.%Y %H:%M} МСК"),
            ("Время в отчёте", "московское, если не указано иное"),
            ("Выручка", "внешние оплаты покупок + покупки с баланса"),
            ("Пополнения", "в выручку не входят: выручка возникает при покупке"),
            ("Учёт", ledger_note),
            (
                "Персональные данные",
                "включены" if command.include_personal else "скрыты",
            ),
        ]


def _project(row: Any, columns: tuple) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for column in columns:
        value = row.get(column.key)
        result[column.key] = column.transform(value) if column.transform else value
    return result


def _summary_rows(totals: Metrics) -> list[dict[str, Any]]:
    return [
        {
            "group": column.group,
            "metric": column.title,
            "value": totals.get(column.key, Decimal("0")),
        }
        for column in METRIC_COLUMNS
    ]


def _region_rows(
    metrics: dict[int | None, Metrics], titles: dict[int, str]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [
        {
            "region": (NO_REGION if rid is None else titles.get(rid, f"#{rid}")),
            **{c.key: values.get(c.key, Decimal("0")) for c in METRIC_COLUMNS},
        }
        for rid, values in metrics.items()
    ]
    rows.sort(key=lambda r: (-r["revenue_total"], r["region"]))
    return rows
