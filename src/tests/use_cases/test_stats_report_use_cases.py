from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest

from src.application.dtos.stats_report import ReportFilter, sum_metrics
from src.application.services.stats_report import sections as registry
from src.application.services.stats_report.sections import METRIC_COLUMNS, SECTIONS
from src.application.use_cases.stats.report import (
    BuildStatsReportRequest,
    BuildStatsReportUseCase,
    GetReportPreviewRequest,
    GetReportPreviewUseCase,
)
from src.domain.enums.ad import AdStatus, AdType
from src.domain.enums.balance import BalanceTransactionKind
from src.domain.enums.payment import PaymentMethod, PaymentPurpose
from src.domain.enums.publication import PublicationStatus
from src.domain.enums.publication_service import (
    PublicationServiceStatus,
    PublicationServiceType,
)
from src.domain.enums.report import ReportSection
from src.domain.enums.role import UserRole


class FakeReportRepo:
    def __init__(self, metrics=None, rows=None, started=None) -> None:
        self.metrics = metrics if metrics is not None else {}
        self.rows = rows or {}
        self.started = started
        self.counted: list[ReportSection] = []

    async def get_region_metrics(self, report_filter):
        return self.metrics

    async def fetch_rows(self, section, report_filter):
        return self.rows.get(section, [])

    async def count_rows(self, section, report_filter):
        self.counted.append(section)
        return len(self.rows.get(section, []))

    async def ledger_started_at(self):
        return self.started


class FakeRegionRepo:
    async def get_all(self):
        return [
            SimpleNamespace(id=1, title="Москва"),
            SimpleNamespace(id=2, title="СПб"),
        ]


class CapturingWriter:
    def __init__(self) -> None:
        self.workbook = None

    def render(self, workbook) -> bytes:
        self.workbook = workbook
        return b"xlsx"


def _build(repo, *sections, include_personal=False, region_ids=()):
    writer = CapturingWriter()
    use_case = BuildStatsReportUseCase(
        report_repo=repo, region_repo=FakeRegionRepo(), writer=writer
    )
    request = BuildStatsReportRequest(
        report_filter=ReportFilter(region_ids=region_ids),
        sections=sections,
        period_label="Месяц",
        include_personal=include_personal,
    )
    return use_case(request), writer


async def test_sheets_follow_requested_sections():
    coro, writer = _build(
        FakeReportRepo(), ReportSection.SUMMARY, ReportSection.PAYMENTS
    )
    file = await coro
    assert file.content == b"xlsx"
    assert file.filename.startswith("stats_") and file.filename.endswith(".xlsx")
    assert [s.title for s in writer.workbook.sheets] == ["Сводка", "Платежи"]


async def test_empty_selection_is_rejected():
    coro, _ = _build(FakeReportRepo())
    with pytest.raises(ValueError):
        await coro


@pytest.mark.parametrize(
    "section",
    [s for s in ReportSection if any(c.personal for c in SECTIONS[s].columns)],
)
async def test_personal_columns_are_dropped_without_flag(section):
    """Значения не должны попасть в файл, а не просто скрыться заголовком."""
    secret = {c.key: "СЕКРЕТ" for c in SECTIONS[section].columns if c.personal}
    repo = FakeReportRepo(rows={section: [{"id": 1, **secret}]})

    coro, writer = _build(repo, section)
    await coro

    sheet = writer.workbook.sheets[0]
    assert not any(c.personal for c in sheet.columns)
    assert "СЕКРЕТ" not in str(sheet.rows)
    assert dict(writer.workbook.params)["Персональные данные"] == "скрыты"


async def test_personal_columns_are_kept_with_flag():
    section = ReportSection.USERS
    repo = FakeReportRepo(rows={section: [{"phone": "+7999"}]})
    coro, writer = _build(repo, section, include_personal=True)
    await coro
    sheet = writer.workbook.sheets[0]
    assert sheet.rows[0]["phone"] == "+7999"
    assert dict(writer.workbook.params)["Персональные данные"] == "включены"


async def test_summary_adds_up_all_regions():
    repo = FakeReportRepo(
        metrics={
            1: {"revenue_total": Decimal("100")},
            2: {"revenue_total": Decimal("50"), "users_new": Decimal("3")},
        }
    )
    coro, writer = _build(repo, ReportSection.SUMMARY)
    await coro
    values = {r["metric"]: r["value"] for r in writer.workbook.sheets[0].rows}
    assert values["Выручка всего, руб."] == Decimal("150")
    assert values["Новых пользователей"] == Decimal("3")
    assert len(values) == len(METRIC_COLUMNS)


async def test_regions_sheet_sorted_by_revenue_with_titles():
    repo = FakeReportRepo(
        metrics={
            1: {"revenue_total": Decimal("10")},
            2: {"revenue_total": Decimal("20")},
            None: {},
            99: {"revenue_total": Decimal("5")},  # регион удалён
        }
    )
    coro, writer = _build(repo, ReportSection.REGIONS)
    await coro
    assert [r["region"] for r in writer.workbook.sheets[0].rows] == [
        "СПб",
        "Москва",
        "#99",
        "Без региона",
    ]


async def test_enum_values_become_labels():
    rows = [
        {
            "method": PaymentMethod.YOOKASSA,
            "purpose": PaymentPurpose.SLOT,
            "amount": Decimal("5"),
        }
    ]
    repo = FakeReportRepo(rows={ReportSection.PAYMENTS: rows})
    coro, writer = _build(repo, ReportSection.PAYMENTS)
    await coro
    row = writer.workbook.sheets[0].rows[0]
    assert (row["method"], row["purpose"]) == ("ЮKassa", "Платный слот")


async def test_store_items_are_counted_and_json_null_is_empty():
    rows = [
        {"store_items": [{"plate": "A"}, {"plate": "B"}]},
        {"store_items": None},
    ]
    repo = FakeReportRepo(rows={ReportSection.ADS: rows})
    coro, writer = _build(repo, ReportSection.ADS)
    await coro
    assert [r["store_items"] for r in writer.workbook.sheets[0].rows] == [2, None]


async def test_params_describe_the_report():
    started = datetime(2026, 11, 1, 9, 0, tzinfo=timezone.utc)
    repo = FakeReportRepo(started=started)
    coro, writer = _build(repo, ReportSection.SUMMARY, region_ids=(1, 2))
    await coro
    params = dict(writer.workbook.params)
    assert params["Период"] == "Месяц"
    assert params["Регионы"] == "Москва, СПб"
    assert "01.11.2026 12:00" in params["Учёт"]


async def test_params_without_ledger_rows():
    coro, writer = _build(FakeReportRepo(), ReportSection.SUMMARY)
    await coro
    params = dict(writer.workbook.params)
    assert params["Регионы"] == "Все регионы"
    assert "журнал ведётся" in params["Учёт"]


async def test_preview_counts_only_row_sections():
    repo = FakeReportRepo(
        metrics={1: {"revenue_total": Decimal("10")}},
        rows={ReportSection.USERS: [{}, {}]},
    )
    result = await GetReportPreviewUseCase(report_repo=repo)(
        GetReportPreviewRequest(
            report_filter=ReportFilter(),
            sections=(ReportSection.SUMMARY, ReportSection.USERS),
        )
    )
    assert result.totals["revenue_total"] == Decimal("10")
    assert result.row_counts == {ReportSection.USERS: 2}
    assert repo.counted == [ReportSection.USERS]


def test_sum_metrics():
    assert sum_metrics(
        [{"a": Decimal("1")}, {"a": Decimal("2"), "b": Decimal("3")}]
    ) == {
        "a": Decimal("3"),
        "b": Decimal("3"),
    }


def test_every_section_is_registered():
    assert set(SECTIONS) == set(ReportSection)


def test_metric_keys_are_unique():
    keys = [c.key for c in METRIC_COLUMNS]
    assert len(keys) == len(set(keys))


@pytest.mark.parametrize(
    ("labels", "enum"),
    [
        (registry.METHOD_LABELS, PaymentMethod),
        (registry.PURPOSE_LABELS, PaymentPurpose),
        (registry.KIND_LABELS, BalanceTransactionKind),
        (registry.AD_TYPE_LABELS, AdType),
        (registry.AD_STATUS_LABELS, AdStatus),
        (registry.PUBLICATION_STATUS_LABELS, PublicationStatus),
        (registry.SERVICE_TYPE_LABELS, PublicationServiceType),
        (registry.SERVICE_STATUS_LABELS, PublicationServiceStatus),
        (registry.ROLE_LABELS, UserRole),
    ],
)
def test_labels_cover_every_enum_value(labels, enum):
    """Новое значение enum не должно уехать в Excel сырым кодом."""
    assert set(labels) == set(enum)
