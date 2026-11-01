from typing import Protocol

from src.domain.entities.balance_transaction import BalanceTransaction


class BalanceLedger(Protocol):
    async def record(self, transaction: BalanceTransaction) -> None:
        """Добавить запись в текущую транзакцию. Коммитит вызывающий — вместе
        с изменением баланса, иначе журнал разойдётся с балансом."""
        ...
