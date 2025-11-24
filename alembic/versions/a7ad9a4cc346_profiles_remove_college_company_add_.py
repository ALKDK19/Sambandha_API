# python
"""profiles: remove college/company; add family_status/family_type; preferences: add preferred_family_type_text

Revision ID: a7ad9a4cc346
Revises: 91b3cd8bcad4
Create Date: 2025-11-06 16:23:26.044202
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a7ad9a4cc346'
down_revision: Union[str, None] = '91b3cd8bcad4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _column_exists(inspector, table_name: str, column_name: str) -> bool:
    try:
        return any(c["name"] == column_name for c in inspector.get_columns(table_name))
    except Exception:
        return False


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Profiles: add family_status, family_type; remove college_name, company_name
    if _table_exists(inspector, "profiles"):
        if not _column_exists(inspector, "profiles", "family_status"):
            op.add_column(
                "profiles",
                sa.Column("family_status", sa.String(), nullable=True),
            )
        if not _column_exists(inspector, "profiles", "family_type"):
            op.add_column(
                "profiles",
                sa.Column("family_type", sa.String(), nullable=True),
            )
        if _column_exists(inspector, "profiles", "college_name"):
            op.drop_column("profiles", "college_name")
        if _column_exists(inspector, "profiles", "company_name"):
            op.drop_column("profiles", "company_name")

    # Preferences: add preferred_family_type_text
    if _table_exists(inspector, "preferences"):
        if not _column_exists(inspector, "preferences", "preferred_family_type_text"):
            op.add_column(
                "preferences",
                sa.Column("preferred_family_type_text", sa.Text(), nullable=True),
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Revert preferences change
    if _table_exists(inspector, "preferences"):
        if _column_exists(inspector, "preferences", "preferred_family_type_text"):
            op.drop_column("preferences", "preferred_family_type_text")

    # Revert profiles changes: remove family fields, restore college/company
    if _table_exists(inspector, "profiles"):
        if _column_exists(inspector, "profiles", "family_status"):
            op.drop_column("profiles", "family_status")
        if _column_exists(inspector, "profiles", "family_type"):
            op.drop_column("profiles", "family_type")
        if not _column_exists(inspector, "profiles", "college_name"):
            op.add_column(
                "profiles",
                sa.Column("college_name", sa.String(), nullable=True),
            )
        if not _column_exists(inspector, "profiles", "company_name"):
            op.add_column(
                "profiles",
                sa.Column("company_name", sa.String(), nullable=True),
            )
