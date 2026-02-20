"""Add RAG parameters to knowledge table

Revision ID: add_knowledge_rag_params
Revises: c440947495f3
Create Date: 2026-02-05 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "add_knowledge_rag_params"
down_revision: Union[str, None] = "c440947495f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add RAG chunking parameters to knowledge table
    with op.batch_alter_table("knowledge", schema=None) as batch_op:
        batch_op.add_column(sa.Column("chunk_size", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("chunk_overlap", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("text_splitter", sa.String(), nullable=True))


def downgrade() -> None:
    # Remove RAG chunking parameters from knowledge table
    with op.batch_alter_table("knowledge", schema=None) as batch_op:
        batch_op.drop_column("text_splitter")
        batch_op.drop_column("chunk_overlap")
        batch_op.drop_column("chunk_size")
