"""add match_type column to matches

Revision ID: b3c2a1d9ef12
Revises: a9257f45fca7
Create Date: 2025-11-04 14:30:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b3c2a1d9ef12'
down_revision = 'a9257f45fca7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Use PostgreSQL's IF NOT EXISTS to avoid errors when the column already exists
    conn = op.get_bind()
    dialect_name = conn.dialect.name
    if dialect_name == 'postgresql':
        op.execute("ALTER TABLE matches ADD COLUMN IF NOT EXISTS match_type VARCHAR DEFAULT 'score_only' NOT NULL")
    else:
        # Fallback: try to add the column, but ignore errors about existing columns
        try:
            op.add_column('matches', sa.Column('match_type', sa.String(), nullable=False, server_default=sa.text("'score_only'")))
        except Exception:
            # If it fails because the column exists, ignore
            pass


def downgrade() -> None:
    # Drop the column if it exists; in PostgreSQL this will error if missing, so use IF EXISTS
    conn = op.get_bind()
    dialect_name = conn.dialect.name
    if dialect_name == 'postgresql':
        op.execute("ALTER TABLE matches DROP COLUMN IF EXISTS match_type")
    else:
        try:
            op.drop_column('matches', 'match_type')
        except Exception:
            pass
