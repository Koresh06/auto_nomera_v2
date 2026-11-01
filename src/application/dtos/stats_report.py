from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from src.domain.enums.report import ReportSection

Metrics = dict[str, Decimal]
RegionMetrics = dict[int | None, Metrics]


class ColumnKind(Enum):
    TEXT = "text"
    INT = "int"
    MONEY = "money"
    DATETIME = "datetime"
    DATE = "date"
    BOOL = "bool"


@dataclass(frozen=True, slots=True)
class ReportColumn:
    key: str
    title: str
    kind: ColumnKind = ColumnKind.TEXT
    # телефоны, контакты, остатки конкретных людей: только супер-админам
    personal: bool = False
    group: str = ""
    transform: Callable[[Any], Any] | None = None


@dataclass(frozen=True, slots=True)
class ReportFilter:
    since_utc: datetime | None = None
    until_utc: datetime | None = None  # не включая
    region_ids: tuple[int, ...] = ()  # пусто — все регионы


@dataclass(frozen=True, slots=True)
class ReportSheet:
    title: str
    columns: tuple[ReportColumn, ...]
    rows: Sequence[Mapping[str, Any]]


@dataclass(frozen=True, slots=True)
class ReportWorkbook:
    params: list[tuple[str, str]]
    sheets: list[ReportSheet]


@dataclass(frozen=True, slots=True)
class ReportFile:
    filename: str
    content: bytes


@dataclass(frozen=True, slots=True)
class ReportPreviewDTO:
    totals: Metrics
    row_counts: dict[ReportSection, int] = field(default_factory=dict)


def sum_metrics(metrics: Iterable[Metrics]) -> Metrics:
    total: Metrics = {}
    for region_metrics in metrics:
        for key, value in region_metrics.items():
            total[key] = total.get(key, Decimal("0")) + value
    return total
