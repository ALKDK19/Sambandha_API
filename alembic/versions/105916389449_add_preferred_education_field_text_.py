"""add preferred_education_field_text field to preferences

Revision ID: 105916389449
Revises: baf104352fbd
Create Date: 2025-11-06 18:33:30.891570

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '105916389449'
down_revision: Union[str, None] = 'baf104352fbd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add the new nullable text column to the preferences table
    op.add_column(
        'preferences',
        sa.Column('preferred_education_field_text', sa.Text(), nullable=True),
    )


def downgrade() -> None:
    # Remove the column when downgrading
    op.drop_column('preferences', 'preferred_education_field_text')
