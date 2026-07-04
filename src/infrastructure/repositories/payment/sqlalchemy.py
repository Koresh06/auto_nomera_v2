from datetime import datetime
from decimal import Decimal

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dtos.payment_stats import MethodStatDTO, PaymentStatsDTO, RegionStatDTO
from src.application.exceptions.payment import PaymentNotFoundByIdException
from src.domain.entities.payment import Payment
from src.application.ports.payment.payment_repo import PaymentRepository
from src.domain.enums.payment import PaymentStatus
from src.infrastructure.database.models import PaymentModel
from src.infrastructure.database.models.region import RegionModel
from src.infrastructure.database.models.user import UserModel


class SQLAlchemyPaymentRepo(PaymentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, payment: Payment) -> Payment:
        model = PaymentModel.from_entity(payment)
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return model.to_entity()

    async def get_by_external_id(self, external_id: str) -> Payment | None:
        query = select(PaymentModel).where(PaymentModel.external_id == external_id)
        result = await self.session.execute(query)
        model = result.scalar_one_or_none()
        return model.to_entity() if model else None
    
    async def save(self, payment: Payment) -> None:
        query = select(PaymentModel).where(PaymentModel.id == payment.id)
        result = await self.session.execute(query)
        model = result.scalar_one_or_none()
        if model is None:
            raise PaymentNotFoundByIdException(payment.id)
        PaymentModel._update_model(model, payment)
        await self.session.flush()

    def _paid_filter(self, since_utc: datetime | None):
        conds = [PaymentModel.status == PaymentStatus.PAID]
        if since_utc is not None:
            conds.append(PaymentModel.paid_at >= since_utc)
        return conds

    async def get_stats(
        self,
        *,
        since_utc: datetime | None = None,
        region_id: int | None = None,
    ) -> PaymentStatsDTO:
        conds = self._paid_filter(since_utc)

        base = select(PaymentModel)
        if region_id is not None:
            base = base.join(UserModel, PaymentModel.user_id == UserModel.id)
            conds.append(UserModel.region_id == region_id)

        # разбивка по методам
        method_q = (
            select(
                PaymentModel.method,
                func.count().label("cnt"),
                func.coalesce(func.sum(PaymentModel.amount), 0).label("amt"),
            )
            .where(and_(*conds))
            .group_by(PaymentModel.method)
        )
        if region_id is not None:
            method_q = method_q.join(
                UserModel, PaymentModel.user_id == UserModel.id
            )

        rows = (await self.session.execute(method_q)).all()

        by_method = [
            MethodStatDTO(
                method=r.method,
                count=r.cnt,
                amount=Decimal(r.amt),
            )
            for r in rows
        ]
        total_count = sum(m.count for m in by_method)
        total_amount = sum((m.amount for m in by_method), Decimal("0"))

        # топ-регион
        top_region = None
        if region_id is None:
            breakdown = await self.get_region_breakdown(since_utc=since_utc)
            if breakdown:
                top_region = max(breakdown, key=lambda r: r.amount)

        return PaymentStatsDTO(
            total_count=total_count,
            total_amount=total_amount,
            by_method=by_method,
            top_region=top_region,
        )

    async def get_region_breakdown(
        self,
        *,
        since_utc: datetime | None = None,
    ) -> list[RegionStatDTO]:
        conds = self._paid_filter(since_utc)

        q = (
            select(
                RegionModel.id,
                RegionModel.title,
                func.count(PaymentModel.id).label("cnt"),
                func.coalesce(func.sum(PaymentModel.amount), 0).label("amt"),
            )
            .join(UserModel, PaymentModel.user_id == UserModel.id)
            .join(RegionModel, UserModel.region_id == RegionModel.id)
            .where(and_(*conds))
            .group_by(RegionModel.id, RegionModel.title)
            .order_by(func.sum(PaymentModel.amount).desc())
        )

        rows = (await self.session.execute(q)).all()
        return [
            RegionStatDTO(
                region_id=r.id,
                region_title=r.title,
                count=r.cnt,
                amount=Decimal(r.amt),
            )
            for r in rows
        ]