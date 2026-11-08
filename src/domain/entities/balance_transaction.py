from dataclasses import dataclass
from decimal import Decimal

from src.domain.entities.base import Entity
from src.domain.entities.user import User
from src.domain.enums.balance import BalanceTransactionKind


@dataclass(kw_only=True)
class BalanceTransaction(Entity):
    """Запись журнала баланса: одно изменение ``users.balance``.

    Сумма со знаком: плюс — зачисление, минус — списание."""

    user_id: int
    amount: Decimal
    balance_after: Decimal
    kind: BalanceTransactionKind
    region_id: int | None = None
    payment_id: int | None = None
    publication_id: int | None = None
    description: str | None = None

    @classmethod
    def of(
        cls,
        user: User,
        *,
        amount: Decimal,
        kind: BalanceTransactionKind,
        region_id: int | None = None,
        payment_id: int | None = None,
        publication_id: int | None = None,
        description: str | None = None,
    ) -> "BalanceTransaction":
        """Вызывать сразу после ``user.charge``/``user.top_up``: остаток берётся
        из пользователя. Регион покупки — регион публикации/слота, поэтому он
        передаётся явно; для остальных операций это регион пользователя."""
        return cls(
            user_id=user.id,
            amount=amount,
            balance_after=user.balance,
            kind=kind,
            region_id=region_id if region_id is not None else user.region_id,
            payment_id=payment_id,
            publication_id=publication_id,
            description=description,
        )
