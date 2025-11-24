"""add embedding_vector field to profiles

Revision ID: 822f0657c766
Revises: 105916389449
Create Date: 2025-11-07 19:14:10.235052

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '822f0657c766'
down_revision: Union[str, None] = '105916389449'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add a binary column `embedding_vector` to `profiles`.
    # Use PostgreSQL's IF NOT EXISTS when possible, otherwise fall back to op.add_column and ignore errors.
    conn = op.get_bind()
    dialect_name = getattr(conn.dialect, "name", None)
    if dialect_name == 'postgresql':
        # bytea is the PostgreSQL binary type
        op.execute("ALTER TABLE profiles ADD COLUMN IF NOT EXISTS embedding_vector bytea")
    else:
        try:
            op.add_column('profiles', sa.Column('embedding_vector', sa.LargeBinary(), nullable=True))
        except Exception:
            # If a column already exists or operation not supported, ignore to make migration idempotent
            pass


def downgrade() -> None:
    # Remove the `embedding_vector` column from `profiles`.
    conn = op.get_bind()
    dialect_name = getattr(conn.dialect, "name", None)
    if dialect_name == 'postgresql':
        op.execute("ALTER TABLE profiles DROP COLUMN IF EXISTS embedding_vector")
    else:
        try:
            op.drop_column('profiles', 'embedding_vector')
        except Exception:
            # If a column doesn't exist or cannot be dropped, ignore
            pass
