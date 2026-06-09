from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.exceptions.payment import PaymentNotFoundByIdException
from src.domain.entities.payment import Payment
from src.application.ports.payment.payment_repo import PaymentRepository
from src.infrastructure.database.models import PaymentModel


class SQLAlchemyPaymentRepo(PaymentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, payment: Payment) -> None:
        model = PaymentModel.from_entity(payment)
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)

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