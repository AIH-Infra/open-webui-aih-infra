"""Add knowledge chunk columns

Revision ID: d4e5f6a7b8c9
Revises: b2c3d4e5f6a7
Create Date: 2026-04-08 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from open_webui.migrations.util import get_existing_tables

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    existing_tables = set(get_existing_tables())

    if "knowledge" in existing_tables:
        with op.batch_alter_table("knowledge", schema=None) as batch_op:
            batch_op.add_column(sa.Column("chunk_size", sa.Integer(), nullable=True))
            batch_op.add_column(sa.Column("chunk_overlap", sa.Integer(), nullable=True))
            batch_op.add_column(sa.Column("text_splitter", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("knowledge", schema=None) as batch_op:
        batch_op.drop_column("text_splitter")
        batch_op.drop_column("chunk_overlap")
        batch_op.drop_column("chunk_size")
