from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Integer, Numeric, String, Enum as SaEnum
from sqlalchemy.orm import Mapped, mapped_column

from src.domain.entities.balance_transaction import BalanceTransaction
from src.domain.enums.balance import BalanceTransactionKind

from .base import BaseModel, CreatedAtMixin


class BalanceTransactionModel(BaseModel, CreatedAtMixin):
    __tablename__ = "balance_transactions"
    __table_args__ = (
        Index("ix__balance_transactions__created_at", "created_at"),
        Index("ix__balance_transactions__user_id", "user_id"),
        Index("ix__balance_transactions__payment_id", "payment_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
    )
    # журнал переживает удаление региона/публикации: деньги уже прошли
    region_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("regions.id", ondelete="SET NULL"),
        nullable=True,
    )
    payment_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("payments.id", ondelete="SET NULL"),
        nullable=True,
    )
    publication_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("publications.id", ondelete="SET NULL"),
        nullable=True,
    )
    kind: Mapped[BalanceTransactionKind] = mapped_column(SaEnum(BalanceTransactionKind))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    balance_after: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    description: Mapped[str | None] = mapped_column(String(256), nullable=True)

    @classmethod
    def from_entity(cls, tx: BalanceTransaction) -> "BalanceTransactionModel":
        return cls(
            user_id=tx.user_id,
            region_id=tx.region_id,
            payment_id=tx.payment_id,
            publication_id=tx.publication_id,
            kind=tx.kind,
            amount=tx.amount,
            balance_after=tx.balance_after,
            description=tx.description,
        )
