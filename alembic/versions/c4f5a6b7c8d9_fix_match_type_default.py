"""fix match_type default to score_only

Revision ID: c4f5a6b7c8d9
Revises: b3c2a1d9ef12
Create Date: 2025-11-04 14:55:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4f5a6b7c8d9'
down_revision: Union[str, None] = 'b3c2a1d9ef12'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Set server default for match_type to 'score_only' and fix existing rows.

    This changes only the column default and updates rows that were incorrectly
    set to 'mutual_like' (or NULL) during the earlier mistaken migration.
    """
    conn = op.get_bind()
    dialect_name = conn.dialect.name

    # Update existing rows that may have the incorrect value
    try:
        op.execute("UPDATE matches SET match_type='score_only' WHERE match_type IS NULL OR match_type='mutual_like'")
    except Exception:
        # If the table/column doesn't exist yet, ignore: the alter below will still set the default for future rows
        pass

    if dialect_name == 'postgresql':
        # Set the column default at the DB level
        op.execute("ALTER TABLE matches ALTER COLUMN match_type SET DEFAULT 'score_only'")
    else:
        # Generic SQLAlchemy alter for other DBs
        op.alter_column('matches', 'match_type', existing_type=sa.String(), server_default=sa.text("'score_only'"))


def downgrade() -> None:
    """Revert the server default back to 'mutual_like'.

    Note: downgrading will change the column default but will NOT revert the
    historical data that was updated in upgrade(). Reverting data would be
    destructive and is intentionally omitted.
    """
    conn = op.get_bind()
    dialect_name = conn.dialect.name

    if dialect_name == 'postgresql':
        op.execute("ALTER TABLE matches ALTER COLUMN match_type SET DEFAULT 'mutual_like'")
    else:
        op.alter_column('matches', 'match_type', existing_type=sa.String(), server_default=sa.text("'mutual_like'"))

