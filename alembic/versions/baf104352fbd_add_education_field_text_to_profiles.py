"""add education_field_text to profiles

Revision ID: baf104352fbd
Revises: a7ad9a4cc346
Create Date: 2025-11-06 18:24:08.975057

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'baf104352fbd'
down_revision: Union[str, None] = 'a7ad9a4cc346'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'profiles',
        sa.Column('education_field_text', sa.String(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('profiles', 'education_field_text')
