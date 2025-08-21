"""Remove total_transactions and total_volume_usd from solana_wallets

Revision ID: 7c422714bd48
Revises: a16d7ab72140
Create Date: 2025-08-20 17:30:13.616991

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7c422714bd48'
down_revision: Union[str, Sequence[str], None] = 'a16d7ab72140'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Remove total_transactions and total_volume_usd columns from solana_wallets table
    op.drop_column('solana_wallets', 'total_transactions')
    op.drop_column('solana_wallets', 'total_volume_usd')


def downgrade() -> None:
    """Downgrade schema."""
    # Add back the columns if needed
    op.add_column('solana_wallets', sa.Column('total_transactions', sa.Integer(), nullable=False, server_default='0', comment='总交易数量'))
    op.add_column('solana_wallets', sa.Column('total_volume_usd', sa.Numeric(precision=15, scale=2), nullable=False, server_default='0.00', comment='总交易额（USD）'))
