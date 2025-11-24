"""remove obsolete address fields and add address

Revision ID: 91b3cd8bcad4
Revises: d1e2f3addc9b
Create Date: 2025-11-06 13:46:10.201200

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '91b3cd8bcad4'
down_revision: Union[str, None] = 'd1e2f3addc9b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # remove obsolete columns
    op.drop_column('profiles', 'current_address')
    op.drop_column('profiles', 'permanent_address')
    op.drop_column('profiles', 'district_text')

    # add a single address field
    op.add_column('profiles', sa.Column('address', sa.Text(), nullable=True))


def downgrade():
    # remove the consolidated address
    op.drop_column('profiles', 'address')

    # restore previous columns
    op.add_column('profiles', sa.Column('district_text', sa.String(), nullable=True))
    op.add_column('profiles', sa.Column('permanent_address', sa.Text(), nullable=True))
    op.add_column('profiles', sa.Column('current_address', sa.Text(), nullable=True))
