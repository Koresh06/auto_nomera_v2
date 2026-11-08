"""Общие фейки для тестов use case'ов."""

from src.domain.entities.balance_transaction import BalanceTransaction


class RecordingLedger:
    def __init__(self) -> None:
        self.records: list[BalanceTransaction] = []

    async def record(self, transaction: BalanceTransaction) -> None:
        self.records.append(transaction)
