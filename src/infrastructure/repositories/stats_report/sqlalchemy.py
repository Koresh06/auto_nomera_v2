from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    ColumnElement,
    Integer,
    Select,
    and_,
    func,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dtos.stats_report import RegionMetrics, ReportFilter
from src.domain.enums.balance import BalanceTransactionKind
from src.domain.enums.payment import PaymentPurpose, PaymentStatus
from src.domain.enums.publication import PublicationStatus
from src.domain.enums.publication_service import PublicationServiceStatus
from src.domain.enums.report import ReportSection
from src.infrastructure.database.models import (
    AdModel,
    BalanceTransactionModel,
    PaymentModel,
    PublicationModel,
    PublicationServiceModel,
    RegionModel,
    UserModel,
)

_PURCHASE_REVENUE = {
    BalanceTransactionKind.SLOT_PURCHASE: "revenue_slot",
    BalanceTransactionKind.SERVICE_PURCHASE: "revenue_publication_service",
    BalanceTransactionKind.PRE_PUBLICATION_PURCHASE: "revenue_pre_publication",
}
_LEDGER_METRICS = {
    BalanceTransactionKind.ADMIN_CREDIT: "balance_admin_credit",
    BalanceTransactionKind.ADMIN_DEBIT: "balance_admin_debit",
    BalanceTransactionKind.COMPENSATION: "balance_compensation",
}
_REGION_BOUND_PURPOSES = (PaymentPurpose.SLOT, PaymentPurpose.PUBLICATION_SERVICE)


def _in_period(column: Any, flt: ReportFilter) -> list[ColumnElement[bool]]:
    conds: list[ColumnElement[bool]] = []
    if flt.since_utc is not None:
        conds.append(column >= flt.since_utc)
    if flt.until_utc is not None:
        conds.append(column < flt.until_utc)
    return conds


def _in_regions(column: Any, flt: ReportFilter) -> list[ColumnElement[bool]]:
    return [column.in_(flt.region_ids)] if flt.region_ids else []


def _paid_time() -> ColumnElement:
    return func.coalesce(PaymentModel.paid_at, PaymentModel.created_at)


def _payment_region() -> ColumnElement:
    """Покупка относится к региону публикации/слота, а не к текущему региону
    пользователя: он мог переехать, или купить слот в другом регионе."""
    slot_region = PaymentModel.meta["return_data"]["slot"]["region_id"].astext.cast(
        Integer
    )
    return func.coalesce(PublicationModel.region_id, slot_region, UserModel.region_id)


def _payments_from(query: Select) -> Select:
    return (
        query.select_from(PaymentModel)
        .join(UserModel, PaymentModel.user_id == UserModel.id)
        .outerjoin(
            PublicationModel,
            and_(
                PaymentModel.purpose_id == PublicationModel.id,
                PaymentModel.purpose.in_(_REGION_BOUND_PURPOSES),
            ),
        )
    )


def _compensated() -> ColumnElement[bool]:
    return PaymentModel.id.in_(
        select(BalanceTransactionModel.payment_id).where(
            BalanceTransactionModel.kind == BalanceTransactionKind.COMPENSATION,
            BalanceTransactionModel.payment_id.is_not(None),
        )
    )


def _ad_title() -> ColumnElement:
    return func.coalesce(AdModel.plate_number, AdModel.shop_name)


class SQLAlchemyStatsReportRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_region_metrics(self, report_filter: ReportFilter) -> RegionMetrics:
        flt = report_filter
        metrics: dict[int | None, defaultdict[str, Decimal]] = {}

        def add(region_id: int | None, key: str, value: Any) -> None:
            bucket = metrics.setdefault(region_id, defaultdict(Decimal))
            bucket[key] += Decimal(value or 0)

        regions = select(RegionModel.id).where(*_in_regions(RegionModel.id, flt))
        for region_id in (await self._session.execute(regions)).scalars():
            metrics.setdefault(region_id, defaultdict(Decimal))

        await self._collect_users(flt, add)
        await self._collect_ads(flt, add)
        await self._collect_publications(flt, add)
        await self._collect_services(flt, add)
        await self._collect_payments(flt, add)
        await self._collect_ledger(flt, add)
        return {rid: dict(values) for rid, values in metrics.items()}

    async def _collect_users(self, flt: ReportFilter, add) -> None:
        period = _in_period(UserModel.created_at, flt)
        new_expr = (
            func.count().filter(and_(*period)) if period else func.count()
        ).label("new")
        q = (
            select(
                UserModel.region_id,
                new_expr,
                func.count().label("total"),
                func.count().filter(UserModel.is_blocked.is_(True)).label("blocked"),
                func.coalesce(func.sum(UserModel.balance), 0).label("balance"),
            )
            .where(*_in_regions(UserModel.region_id, flt))
            .group_by(UserModel.region_id)
        )
        for r in await self._session.execute(q):
            add(r.region_id, "users_new", r.new)
            add(r.region_id, "users_total", r.total)
            add(r.region_id, "users_blocked", r.blocked)
            add(r.region_id, "balance_now", r.balance)

    async def _collect_ads(self, flt: ReportFilter, add) -> None:
        q = (
            select(AdModel.region_id, AdModel.ad_type, func.count().label("cnt"))
            .where(
                *_in_period(AdModel.created_at, flt),
                *_in_regions(AdModel.region_id, flt),
            )
            .group_by(AdModel.region_id, AdModel.ad_type)
        )
        for r in await self._session.execute(q):
            add(r.region_id, "ads_new", r.cnt)
            add(r.region_id, f"ads_{r.ad_type.value}", r.cnt)

    async def _collect_publications(self, flt: ReportFilter, add) -> None:
        q = (
            select(
                PublicationModel.region_id,
                PublicationModel.status,
                func.count().label("cnt"),
            )
            .where(
                *_in_period(PublicationModel.publish_at_utc, flt),
                *_in_regions(PublicationModel.region_id, flt),
            )
            .group_by(PublicationModel.region_id, PublicationModel.status)
        )
        for r in await self._session.execute(q):
            add(r.region_id, "publications_total", r.cnt)
            add(r.region_id, f"publications_{r.status.value}", r.cnt)

    async def _collect_services(self, flt: ReportFilter, add) -> None:
        q = (
            select(
                PublicationModel.region_id,
                PublicationServiceModel.type,
                func.count().label("cnt"),
                func.coalesce(func.sum(PublicationServiceModel.price_paid), 0).label(
                    "amt"
                ),
            )
            .join(
                PublicationModel,
                PublicationServiceModel.publication_id == PublicationModel.id,
            )
            .where(
                PublicationServiceModel.status.in_(
                    [PublicationServiceStatus.ACTIVE, PublicationServiceStatus.USED]
                ),
                *_in_period(PublicationServiceModel.created_at, flt),
                *_in_regions(PublicationModel.region_id, flt),
            )
            .group_by(PublicationModel.region_id, PublicationServiceModel.type)
        )
        for r in await self._session.execute(q):
            add(r.region_id, "services_total", r.cnt)
            add(r.region_id, "services_amount", r.amt)
            add(r.region_id, f"services_{r.type.value}", r.cnt)

    async def _collect_payments(self, flt: ReportFilter, add) -> None:
        region = _payment_region()
        # подзапрос: выражения с bind-параметрами (путь в JSON, enum) нельзя
        # повторить в GROUP BY — Postgres считает их разными
        paid = (
            _payments_from(
                select(
                    region.label("region_id"),
                    PaymentModel.method,
                    PaymentModel.purpose,
                    _compensated().label("compensated"),
                    PaymentModel.amount,
                )
            )
            .where(
                PaymentModel.status == PaymentStatus.PAID,
                *_in_period(_paid_time(), flt),
                *_in_regions(region, flt),
            )
            .subquery()
        )
        q = select(
            paid.c.region_id,
            paid.c.method,
            paid.c.purpose,
            paid.c.compensated,
            func.count().label("cnt"),
            func.coalesce(func.sum(paid.c.amount), 0).label("amt"),
        ).group_by(paid.c.region_id, paid.c.method, paid.c.purpose, paid.c.compensated)

        for r in await self._session.execute(q):
            add(r.region_id, "inflow_total", r.amt)
            add(r.region_id, "inflow_count", r.cnt)
            add(r.region_id, f"inflow_{r.method.value}", r.amt)
            if r.purpose == PaymentPurpose.BALANCE_TOPUP:
                add(r.region_id, "topup_total", r.amt)
            elif not r.compensated:
                add(r.region_id, "revenue_total", r.amt)
                add(r.region_id, "revenue_count", r.cnt)
                add(r.region_id, "revenue_direct", r.amt)
                add(r.region_id, f"revenue_{r.purpose.value}", r.amt)

    async def _collect_ledger(self, flt: ReportFilter, add) -> None:
        tx = BalanceTransactionModel
        q = (
            select(
                tx.region_id,
                tx.kind,
                func.count().label("cnt"),
                func.coalesce(func.sum(tx.amount), 0).label("amt"),
            )
            .where(
                *_in_period(tx.created_at, flt),
                *_in_regions(tx.region_id, flt),
            )
            .group_by(tx.region_id, tx.kind)
        )
        for r in await self._session.execute(q):
            amount = abs(Decimal(r.amt))
            if r.kind in _PURCHASE_REVENUE:
                add(r.region_id, "revenue_total", amount)
                add(r.region_id, "revenue_count", r.cnt)
                add(r.region_id, "revenue_from_balance", amount)
                add(r.region_id, _PURCHASE_REVENUE[r.kind], amount)
            elif r.kind in _LEDGER_METRICS:
                add(r.region_id, _LEDGER_METRICS[r.kind], amount)

    async def fetch_rows(
        self, section: ReportSection, report_filter: ReportFilter
    ) -> Sequence[Mapping[str, Any]]:
        result = await self._session.execute(self._query(section, report_filter))
        return result.mappings().all()

    async def count_rows(
        self, section: ReportSection, report_filter: ReportFilter
    ) -> int:
        inner = self._query(section, report_filter).order_by(None).subquery()
        q = select(func.count()).select_from(inner)
        return (await self._session.execute(q)).scalar() or 0

    async def ledger_started_at(self) -> datetime | None:
        q = select(func.min(BalanceTransactionModel.created_at))
        return (await self._session.execute(q)).scalar()

    def _query(self, section: ReportSection, flt: ReportFilter) -> Select:
        match section:
            case ReportSection.PAYMENTS:
                return self._payments(flt)
            case ReportSection.BALANCE:
                return self._balance(flt)
            case ReportSection.USERS:
                return self._users(flt)
            case ReportSection.ADS:
                return self._ads(flt)
            case ReportSection.PUBLICATIONS:
                return self._publications(flt)
            case ReportSection.SERVICES:
                return self._services(flt)
        raise ValueError(f"Раздел {section} не строится из строк")

    @staticmethod
    def _payments(flt: ReportFilter) -> Select:
        region = _payment_region()
        q = _payments_from(
            select(
                PaymentModel.id,
                _paid_time().label("paid_at"),
                select(RegionModel.title)
                .where(RegionModel.id == region)
                .scalar_subquery()
                .label("region"),
                PaymentModel.user_id,
                UserModel.tg_id,
                UserModel.username,
                UserModel.full_name,
                UserModel.phone,
                PaymentModel.method,
                PaymentModel.purpose,
                PaymentModel.amount,
                PaymentModel.currency,
                _compensated().label("compensated"),
                PaymentModel.description,
                PaymentModel.external_id,
            )
        )
        return q.where(
            PaymentModel.status == PaymentStatus.PAID,
            *_in_period(_paid_time(), flt),
            *_in_regions(region, flt),
        ).order_by(PaymentModel.id.desc())

    @staticmethod
    def _balance(flt: ReportFilter) -> Select:
        tx = BalanceTransactionModel
        return (
            select(
                tx.id,
                tx.created_at,
                RegionModel.title.label("region"),
                tx.user_id,
                UserModel.tg_id,
                UserModel.username,
                tx.kind,
                tx.amount,
                tx.balance_after,
                tx.description,
                tx.payment_id,
                tx.publication_id,
            )
            .select_from(tx)
            .join(UserModel, tx.user_id == UserModel.id)
            .outerjoin(RegionModel, tx.region_id == RegionModel.id)
            .where(*_in_period(tx.created_at, flt), *_in_regions(tx.region_id, flt))
            .order_by(tx.id.desc())
        )

    @staticmethod
    def _users(flt: ReportFilter) -> Select:
        ads = (
            select(AdModel.user_id, func.count().label("cnt"))
            .group_by(AdModel.user_id)
            .subquery()
        )
        published = (
            select(AdModel.user_id, func.count().label("cnt"))
            .join(PublicationModel, PublicationModel.ad_id == AdModel.id)
            .where(PublicationModel.status == PublicationStatus.PUBLISHED)
            .group_by(AdModel.user_id)
            .subquery()
        )
        paid = (
            select(PaymentModel.user_id, func.sum(PaymentModel.amount).label("amt"))
            .where(PaymentModel.status == PaymentStatus.PAID)
            .group_by(PaymentModel.user_id)
            .subquery()
        )
        tx = BalanceTransactionModel
        spent = (
            select(tx.user_id, func.sum(-tx.amount).label("amt"))
            .where(tx.kind.in_(_PURCHASE_REVENUE))
            .group_by(tx.user_id)
            .subquery()
        )
        return (
            select(
                UserModel.id,
                UserModel.tg_id,
                UserModel.username,
                UserModel.full_name,
                UserModel.phone,
                RegionModel.title.label("region"),
                UserModel.created_at,
                UserModel.role,
                UserModel.is_blocked,
                UserModel.is_payment_blocked,
                UserModel.balance,
                UserModel.pre_publication_expires_at,
                func.coalesce(ads.c.cnt, 0).label("ads_count"),
                func.coalesce(published.c.cnt, 0).label("published_count"),
                func.coalesce(paid.c.amt, 0).label("paid_total"),
                func.coalesce(spent.c.amt, 0).label("spent_total"),
            )
            .select_from(UserModel)
            .outerjoin(RegionModel, UserModel.region_id == RegionModel.id)
            .outerjoin(ads, ads.c.user_id == UserModel.id)
            .outerjoin(published, published.c.user_id == UserModel.id)
            .outerjoin(paid, paid.c.user_id == UserModel.id)
            .outerjoin(spent, spent.c.user_id == UserModel.id)
            .where(
                *_in_period(UserModel.created_at, flt),
                *_in_regions(UserModel.region_id, flt),
            )
            .order_by(UserModel.id.desc())
        )

    @staticmethod
    def _ads(flt: ReportFilter) -> Select:
        publications = (
            select(PublicationModel.ad_id, func.count().label("cnt"))
            .group_by(PublicationModel.ad_id)
            .subquery()
        )
        return (
            select(
                AdModel.id,
                AdModel.created_at,
                RegionModel.title.label("region"),
                AdModel.user_id,
                UserModel.tg_id,
                AdModel.ad_type,
                AdModel.status,
                _ad_title().label("title"),
                AdModel.city,
                AdModel.price,
                AdModel.store_items,
                AdModel.username.label("contact_username"),
                AdModel.phone.label("contact_phone"),
                func.coalesce(publications.c.cnt, 0).label("publications_count"),
            )
            .select_from(AdModel)
            .join(UserModel, AdModel.user_id == UserModel.id)
            .outerjoin(RegionModel, AdModel.region_id == RegionModel.id)
            .outerjoin(publications, publications.c.ad_id == AdModel.id)
            .where(
                *_in_period(AdModel.created_at, flt),
                *_in_regions(AdModel.region_id, flt),
            )
            .order_by(AdModel.id.desc())
        )

    @staticmethod
    def _publications(flt: ReportFilter) -> Select:
        services = (
            select(PublicationServiceModel.publication_id, func.count().label("cnt"))
            .group_by(PublicationServiceModel.publication_id)
            .subquery()
        )
        return (
            select(
                PublicationModel.id,
                PublicationModel.ad_id,
                RegionModel.title.label("region"),
                AdModel.user_id,
                UserModel.tg_id,
                AdModel.ad_type,
                _ad_title().label("title"),
                PublicationModel.status,
                PublicationModel.slot_day,
                PublicationModel.slot_time,
                PublicationModel.publish_at_utc,
                PublicationModel.published_at_utc,
                PublicationModel.is_child,
                func.coalesce(services.c.cnt, 0).label("services_count"),
            )
            .select_from(PublicationModel)
            .join(AdModel, PublicationModel.ad_id == AdModel.id)
            .join(UserModel, AdModel.user_id == UserModel.id)
            .outerjoin(RegionModel, PublicationModel.region_id == RegionModel.id)
            .outerjoin(services, services.c.publication_id == PublicationModel.id)
            .where(
                *_in_period(PublicationModel.publish_at_utc, flt),
                *_in_regions(PublicationModel.region_id, flt),
            )
            .order_by(PublicationModel.id.desc())
        )

    @staticmethod
    def _services(flt: ReportFilter) -> Select:
        return (
            select(
                PublicationServiceModel.id,
                PublicationServiceModel.created_at,
                RegionModel.title.label("region"),
                PublicationServiceModel.publication_id,
                _ad_title().label("title"),
                AdModel.user_id,
                UserModel.tg_id,
                PublicationServiceModel.type,
                PublicationServiceModel.status,
                PublicationServiceModel.price_paid,
            )
            .select_from(PublicationServiceModel)
            .join(
                PublicationModel,
                PublicationServiceModel.publication_id == PublicationModel.id,
            )
            .join(AdModel, PublicationModel.ad_id == AdModel.id)
            .join(UserModel, AdModel.user_id == UserModel.id)
            .outerjoin(RegionModel, PublicationModel.region_id == RegionModel.id)
            .where(
                *_in_period(PublicationServiceModel.created_at, flt),
                *_in_regions(PublicationModel.region_id, flt),
            )
            .order_by(PublicationServiceModel.id.desc())
        )
