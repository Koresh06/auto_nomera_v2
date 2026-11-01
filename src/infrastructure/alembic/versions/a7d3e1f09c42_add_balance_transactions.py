"""add balance_transactions

Revision ID: a7d3e1f09c42
Revises: 5e1740d656ab

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a7d3e1f09c42"
down_revision: Union[str, Sequence[str], None] = "5e1740d656ab"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "balance_transactions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("region_id", sa.Integer(), nullable=True),
        sa.Column("payment_id", sa.Integer(), nullable=True),
        sa.Column("publication_id", sa.Integer(), nullable=True),
        sa.Column(
            "kind",
            sa.Enum(
                "TOPUP",
                "COMPENSATION",
                "ADMIN_CREDIT",
                "ADMIN_DEBIT",
                "SLOT_PURCHASE",
                "SERVICE_PURCHASE",
                "PRE_PUBLICATION_PURCHASE",
                name="balancetransactionkind",
            ),
            nullable=False,
        ),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("balance_after", sa.Numeric(12, 2), nullable=False),
        sa.Column("description", sa.String(length=256), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="balance_transactions_user_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["region_id"],
            ["regions.id"],
            name="balance_transactions_region_id_fkey",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["payment_id"],
            ["payments.id"],
            name="balance_transactions_payment_id_fkey",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["publication_id"],
            ["publications.id"],
            name="balance_transactions_publication_id_fkey",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk__balance_transactions"),
    )
    op.create_index(
        "ix__balance_transactions__created_at", "balance_transactions", ["created_at"]
    )
    op.create_index(
        "ix__balance_transactions__user_id", "balance_transactions", ["user_id"]
    )
    op.create_index(
        "ix__balance_transactions__payment_id", "balance_transactions", ["payment_id"]
    )


def downgrade() -> None:
    op.drop_index(
        "ix__balance_transactions__payment_id", table_name="balance_transactions"
    )
    op.drop_index(
        "ix__balance_transactions__user_id", table_name="balance_transactions"
    )
    op.drop_index(
        "ix__balance_transactions__created_at", table_name="balance_transactions"
    )
    op.drop_table("balance_transactions")
    sa.Enum(name="balancetransactionkind").drop(op.get_bind(), checkfirst=True)
