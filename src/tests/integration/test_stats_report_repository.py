"""Запросы отчёта против реального Postgres: выручка без двойного счёта,
привязка к регионам, границы периода, строки всех разделов."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from src.application.dtos.stats_report import ReportFilter, sum_metrics
from src.domain.entities.balance_transaction import BalanceTransaction
from src.domain.entities.publication_service import PublicationService
from src.domain.enums.ad import AdStatus, AdType
from src.domain.enums.balance import BalanceTransactionKind as Kind
from src.domain.enums.payment import PaymentMethod, PaymentPurpose, PaymentStatus
from src.domain.enums.publication import PublicationStatus
from src.domain.enums.publication_service import (
    PublicationServiceStatus,
    PublicationServiceType,
)
from src.domain.enums.report import ReportSection
from src.infrastructure.repositories.balance.sqlalchemy import SQLAlchemyBalanceLedger
from src.infrastructure.repositories.stats_report.sqlalchemy import (
    SQLAlchemyStatsReportRepo,
)

from .factories import (
    make_ad,
    make_payment,
    make_publication,
    make_region,
    make_user,
    slot,
)

NOW = datetime(2026, 10, 15, 12, 0, tzinfo=timezone.utc)


def repo(session):
    return SQLAlchemyStatsReportRepo(session)


async def _ledger(session, user, amount, kind, **kw):
    await SQLAlchemyBalanceLedger(session).record(
        BalanceTransaction.of(user, amount=Decimal(amount), kind=kind, **kw)
    )


async def _total(session, **flt):
    metrics = await repo(session).get_region_metrics(ReportFilter(**flt))
    return sum_metrics(metrics.values())


async def _world(session):
    r1 = await make_region(session, title="Москва", channel_id=-1)
    r2 = await make_region(session, title="СПб", channel_id=-2)
    u1 = await make_user(session, r1.id, username="ivan", phone="+7900")
    u2 = await make_user(session, r2.id)
    return r1, r2, u1, u2


async def test_topup_then_purchase_from_balance_is_not_counted_twice(session):
    """Пополнил на 1000, потратил 300: поступило 1000, выручка 300."""
    r1, _, u1, _ = await _world(session)
    await make_payment(session, u1, external_id="t", amount=Decimal("1000"))
    await _ledger(session, u1, "1000", Kind.TOPUP)
    await _ledger(session, u1, "-300", Kind.SLOT_PURCHASE)

    totals = await _total(session)

    assert totals["inflow_total"] == Decimal("1000")
    assert totals["topup_total"] == Decimal("1000")
    assert totals["revenue_total"] == Decimal("300")
    assert totals["revenue_from_balance"] == Decimal("300")
    assert totals["revenue_slot"] == Decimal("300")
    assert totals["revenue_count"] == 1
    assert "revenue_direct" not in totals


async def test_direct_payments_count_as_revenue_by_purpose(session):
    _, _, u1, _ = await _world(session)
    for i, (purpose, amount) in enumerate(
        [
            (PaymentPurpose.SLOT, "100"),
            (PaymentPurpose.PUBLICATION_SERVICE, "200"),
            (PaymentPurpose.PRE_PUBLICATION, "400"),
        ]
    ):
        await make_payment(
            session, u1, external_id=f"p{i}", amount=Decimal(amount), purpose=purpose
        )
    await _ledger(session, u1, "-50", Kind.SERVICE_PURCHASE)
    await _ledger(session, u1, "-25", Kind.PRE_PUBLICATION_PURCHASE)

    totals = await _total(session)

    assert totals["revenue_slot"] == Decimal("100")
    assert totals["revenue_publication_service"] == Decimal("250")
    assert totals["revenue_pre_publication"] == Decimal("425")
    assert totals["revenue_total"] == Decimal("775")
    assert totals["revenue_direct"] == Decimal("700")
    assert totals["revenue_from_balance"] == Decimal("75")
    assert totals["revenue_count"] == 5
    assert totals["inflow_yookassa"] == Decimal("700")


async def test_compensated_payment_is_inflow_but_not_revenue(session):
    _, _, u1, _ = await _world(session)
    payment = await make_payment(
        session,
        u1,
        external_id="c",
        amount=Decimal("150"),
        purpose=PaymentPurpose.PUBLICATION_SERVICE,
    )
    await _ledger(session, u1, "150", Kind.COMPENSATION, payment_id=payment.id)

    totals = await _total(session)

    assert totals["inflow_total"] == Decimal("150")
    assert totals["balance_compensation"] == Decimal("150")
    assert totals.get("revenue_total", Decimal("0")) == 0

    rows = await repo(session).fetch_rows(ReportSection.PAYMENTS, ReportFilter())
    assert rows[0]["compensated"] is True


async def test_admin_adjustments_are_not_revenue(session):
    _, _, u1, _ = await _world(session)
    await _ledger(session, u1, "500", Kind.ADMIN_CREDIT)
    await _ledger(session, u1, "-200", Kind.ADMIN_DEBIT)

    totals = await _total(session)

    assert totals["balance_admin_credit"] == Decimal("500")
    assert totals["balance_admin_debit"] == Decimal("200")
    assert totals.get("revenue_total", Decimal("0")) == 0


async def test_pending_payment_is_ignored(session):
    _, _, u1, _ = await _world(session)
    await make_payment(
        session, u1, external_id="w", status=PaymentStatus.PENDING, amount=Decimal("9")
    )
    assert "inflow_total" not in await _total(session)
    assert await repo(session).count_rows(ReportSection.PAYMENTS, ReportFilter()) == 0


async def test_purchases_go_to_region_of_the_publication_not_the_user(session):
    """Житель Москвы покупает слот и услугу в объявлении СПб."""
    r1, r2, u1, _ = await _world(session)
    ad = await make_ad(session, u1, region_id=r2.id)
    pub = await make_publication(session, ad)
    await make_payment(
        session,
        u1,
        external_id="by-pub",
        amount=Decimal("100"),
        purpose=PaymentPurpose.PUBLICATION_SERVICE,
        purpose_id=pub.id,
    )
    await make_payment(
        session,
        u1,
        external_id="by-meta",
        amount=Decimal("70"),
        purpose=PaymentPurpose.SLOT,
        meta={"return_data": {"slot": {"region_id": r2.id}}},
    )
    await make_payment(session, u1, external_id="own", amount=Decimal("10"))
    await _ledger(session, u1, "-30", Kind.SLOT_PURCHASE, region_id=r2.id)

    metrics = await repo(session).get_region_metrics(ReportFilter())

    assert metrics[r2.id]["revenue_total"] == Decimal("200")
    assert metrics[r1.id]["inflow_total"] == Decimal("10")
    assert metrics[r1.id].get("revenue_total", Decimal("0")) == 0

    rows = await repo(session).fetch_rows(
        ReportSection.PAYMENTS, ReportFilter(region_ids=(r2.id,))
    )
    assert {r["external_id"] for r in rows} == {"by-pub", "by-meta"}
    assert {r["region"] for r in rows} == {"СПб"}


async def test_service_payment_purpose_id_is_not_read_for_topups(session):
    """purpose_id пополнения — не id публикации: случайное совпадение номера
    не должно увести платёж в чужой регион."""
    r1, r2, u1, _ = await _world(session)
    ad = await make_ad(session, await make_user(session, r2.id))
    pub = await make_publication(session, ad)
    await make_payment(session, u1, external_id="t", purpose_id=pub.id)

    metrics = await repo(session).get_region_metrics(ReportFilter())

    assert metrics[r1.id]["inflow_total"] == Decimal("100")
    assert "inflow_total" not in metrics[r2.id]


async def test_region_filter_keeps_empty_regions_and_excludes_others(session):
    r1, r2, u1, u2 = await _world(session)
    r3 = await make_region(session, title="Пусто", channel_id=-3)
    await make_payment(session, u2, external_id="x")

    metrics = await repo(session).get_region_metrics(
        ReportFilter(region_ids=(r1.id, r3.id))
    )

    assert set(metrics) == {r1.id, r3.id}
    assert metrics[r3.id] == {}
    assert sum_metrics(metrics.values())["users_total"] == 1


async def test_period_lower_bound_inclusive_upper_exclusive(session):
    _, _, u1, _ = await _world(session)
    day = timedelta(days=1)
    for name, moment in {"before": NOW - day, "start": NOW, "end": NOW + day}.items():
        await make_payment(session, u1, external_id=name, paid_at=moment)

    flt = ReportFilter(since_utc=NOW, until_utc=NOW + day)
    rows = await repo(session).fetch_rows(ReportSection.PAYMENTS, flt)

    assert [r["external_id"] for r in rows] == ["start"]
    assert (await _total(session, since_utc=NOW, until_utc=NOW + day))[
        "inflow_count"
    ] == 1


async def test_counters_of_now_ignore_the_period(session):
    _, _, u1, u2 = await _world(session)
    future = NOW + timedelta(days=3650)

    totals = await _total(session, since_utc=future)

    assert totals["users_total"] == 2
    assert "users_new" not in totals or totals["users_new"] == 0


async def test_user_metrics(session):
    r1, _, u1, _ = await _world(session)
    await make_user(session, r1.id, is_blocked=True, balance=Decimal("40"))

    totals = await _total(session)

    assert totals["users_new"] == 3
    assert totals["users_blocked"] == 1
    assert totals["balance_now"] == Decimal("40")


async def test_content_metrics_and_canceled_services_excluded(session):
    _, _, u1, _ = await _world(session)
    ad = await make_ad(session, u1, ad_type=AdType.BUY)
    await make_ad(session, u1, ad_type=AdType.STORE)
    services = [
        PublicationService(type=PublicationServiceType.PIN, price_paid=100),
        PublicationService(
            type=PublicationServiceType.HIGHLIGHT,
            price_paid=999,
            status=PublicationServiceStatus.CANCELED,
        ),
    ]
    await make_publication(
        session, ad, status=PublicationStatus.PUBLISHED, services=services
    )

    totals = await _total(session)

    assert totals["ads_new"] == 2
    assert totals["ads_buy"] == 1
    assert totals["ads_store"] == 1
    assert totals["publications_total"] == 1
    assert totals["publications_published"] == 1
    assert totals["services_total"] == 1
    assert totals["services_pin"] == 1
    assert totals["services_amount"] == Decimal("100")


@pytest.mark.parametrize(
    "section",
    [
        s
        for s in ReportSection
        if s not in (ReportSection.SUMMARY, ReportSection.REGIONS)
    ],
)
async def test_empty_database_gives_empty_rows(session, section):
    assert await repo(session).fetch_rows(section, ReportFilter()) == []
    assert await repo(session).count_rows(section, ReportFilter()) == 0


async def test_all_sections_return_rows_with_expected_keys(session):
    from src.application.services.stats_report.sections import SECTIONS

    r1, _, u1, _ = await _world(session)
    sale = await make_ad(session, u1, status=AdStatus.PUBLISHED)
    store = await make_ad(session, u1, ad_type=AdType.STORE, plate="С777СС77")
    pub = await make_publication(
        session,
        sale,
        status=PublicationStatus.PUBLISHED,
        slot_key=slot(r1.id, date(2026, 10, 15)),
        services=[PublicationService(type=PublicationServiceType.PIN, price_paid=5)],
    )
    await make_publication(session, store)
    await make_payment(
        session, u1, external_id="pay", method=PaymentMethod.CRYPTO, amount=Decimal("7")
    )
    await _ledger(session, u1, "-3", Kind.SERVICE_PURCHASE, publication_id=pub.id)
    await session.commit()

    for section, definition in SECTIONS.items():
        if section in (ReportSection.SUMMARY, ReportSection.REGIONS):
            continue
        rows = await repo(session).fetch_rows(section, ReportFilter())
        assert rows, section
        assert await repo(session).count_rows(section, ReportFilter()) == len(rows)
        missing = {c.key for c in definition.columns} - set(rows[0].keys())
        assert not missing, (section, missing)


async def test_users_section_aggregates_activity(session):
    r1, _, u1, _ = await _world(session)
    ad = await make_ad(session, u1)
    await make_ad(session, u1, plate="В222ВВ77")
    await make_publication(session, ad, status=PublicationStatus.PUBLISHED)
    await make_publication(session, ad, status=PublicationStatus.CANCELED)
    await make_payment(session, u1, external_id="a", amount=Decimal("100"))
    await make_payment(session, u1, external_id="b", amount=Decimal("50"))
    await _ledger(session, u1, "-30", Kind.SLOT_PURCHASE)
    await _ledger(session, u1, "500", Kind.ADMIN_CREDIT)

    rows = await repo(session).fetch_rows(
        ReportSection.USERS, ReportFilter(region_ids=(r1.id,))
    )

    assert len(rows) == 1
    row = rows[0]
    assert row["region"] == "Москва"
    assert (row["ads_count"], row["published_count"]) == (2, 1)
    assert row["paid_total"] == Decimal("150")
    assert row["spent_total"] == Decimal("30")


async def test_store_ad_uses_shop_name_and_counts_items(session):
    _, _, u1, _ = await _world(session)
    await make_ad(session, u1, ad_type=AdType.STORE)
    await make_ad(session, u1)  # у обычного объявления store_items — JSON null

    rows = await repo(session).fetch_rows(ReportSection.ADS, ReportFilter())

    by_type = {r["ad_type"]: r for r in rows}
    assert by_type[AdType.STORE]["title"] == "Shop"
    assert len(by_type[AdType.STORE]["store_items"]) == 1
    assert not by_type[AdType.SALE]["store_items"]


async def test_ledger_started_at(session):
    assert await repo(session).ledger_started_at() is None
    _, _, u1, _ = await _world(session)
    await _ledger(session, u1, "1", Kind.ADMIN_CREDIT)
    assert await repo(session).ledger_started_at() is not None
