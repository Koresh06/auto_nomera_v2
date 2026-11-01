from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.balance_transaction import BalanceTransaction
from src.infrastructure.database.models.balance_transaction import (
    BalanceTransactionModel,
)


class SQLAlchemyBalanceLedger:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(self, transaction: BalanceTransaction) -> None:
        self._session.add(BalanceTransactionModel.from_entity(transaction))
        await self._session.flush()
