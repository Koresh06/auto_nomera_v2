"""add legacy_id to ads (temporary, for migration)

Временная колонка: связывает объявления с задачами старого Redis
(publish_ad_{legacy_id}). После переноса и ресинхронизации задач
можно удалить: op.drop_column("ads", "legacy_id").

Revision ID: c2a5d1e88f30
Revises: b1f4c9a72e10
Create Date: 2026-07-31

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "c2a5d1e88f30"
down_revision: Union[str, None] = "b1f4c9a72e10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("ads", sa.Column("legacy_id", sa.Integer(), nullable=True))
    op.create_index("ix__ads_legacy_id", "ads", ["legacy_id"])


def downgrade() -> None:
    op.drop_index("ix__ads_legacy_id", table_name="ads")
    op.drop_column("ads", "legacy_id")
