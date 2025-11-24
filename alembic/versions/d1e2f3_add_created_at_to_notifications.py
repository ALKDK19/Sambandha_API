"""add created_at to notifications

Revision ID: d1e2f3addc9b
Revises: c4f5a6b7c8d9
Create Date: 2025-11-04 00:00:00.000000
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'd1e2f3addc9b'
down_revision = 'c4f5a6b7c8d9'
branch_labels = None
depends_on = None


def upgrade():
    # Add the created_at column with server default now()
    op.add_column('notifications',
                  sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False))


def downgrade():
    op.drop_column('notifications', 'created_at')
