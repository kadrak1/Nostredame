"""add_order_source_fix_strength_range

Revision ID: 4812ea6b4d24
Revises: 5de59e930c0a
Create Date: 2026-03-09 00:05:13.220808
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4812ea6b4d24'
down_revision: Union[str, None] = '5de59e930c0a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('hookah_orders', recreate='auto') as batch_op:
        # server_default quoted for PostgreSQL Enum compatibility
        batch_op.add_column(
            sa.Column(
                'source',
                sa.Enum('booking_preorder', 'qr_table', 'telegram', name='ordersource'),
                nullable=False,
                server_default="'booking_preorder'",
            )
        )
        # Fix strength constraint from 1-5 to 1-10 (spec requires 1-10 scale).
        # Use short logical name — naming convention expands to ck_hookah_orders_strength_range.
        batch_op.drop_constraint('strength_range', type_='check')
        batch_op.create_check_constraint(
            'strength_range',
            'strength >= 1 AND strength <= 10',
        )


def downgrade() -> None:
    with op.batch_alter_table('hookah_orders', recreate='auto') as batch_op:
        batch_op.drop_column('source')
        batch_op.drop_constraint('strength_range', type_='check')
        batch_op.create_check_constraint(
            'strength_range',
            'strength >= 1 AND strength <= 5',
        )
