"""drop unique constraint on regions.channel_id

Два региона могут вещать в один канал (Тыва/Хакасия, Крым/Севастополь).

Revision ID: b1f4c9a72e10
Revises: ccf527993388
Create Date: 2026-07-19

"""

from typing import Sequence, Union

from alembic import op


revision: str = "b1f4c9a72e10"
down_revision: Union[str, None] = "ccf527993388"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("uq__regions__channel_id", "regions", type_="unique")
    op.create_index("ix__regions__channel_id", "regions", ["channel_id"])


def downgrade() -> None:
    op.drop_index("ix__regions__channel_id", table_name="regions")
    op.create_unique_constraint("uq__regions__channel_id", "regions", ["channel_id"])
