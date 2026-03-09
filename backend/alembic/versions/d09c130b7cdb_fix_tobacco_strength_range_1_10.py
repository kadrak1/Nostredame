""""fix_tobacco_strength_range_1_10"

Revision ID: d09c130b7cdb
Revises: 37e662d11adf
Create Date: 2026-03-09 15:17:40.914722
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd09c130b7cdb'
down_revision: Union[str, None] = '37e662d11adf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLite doesn't support ALTER CONSTRAINT — use batch to recreate the table
    with op.batch_alter_table("tobaccos", recreate="always") as batch_op:
        batch_op.drop_constraint("strength_range", type_="check")
        batch_op.create_check_constraint(
            "strength_range", "strength >= 1 AND strength <= 10"
        )


def downgrade() -> None:
    with op.batch_alter_table("tobaccos", recreate="always") as batch_op:
        batch_op.drop_constraint("strength_range", type_="check")
        batch_op.create_check_constraint(
            "strength_range", "strength >= 1 AND strength <= 5"
        )
