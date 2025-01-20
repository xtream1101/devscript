"""add pending_email to User

Revision ID: e1e5a2f3397a
Revises: 2dde5025784a
Create Date: 2025-01-19 21:34:19.490243

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e1e5a2f3397a"
down_revision: Union[str, None] = "2dde5025784a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "snippets",
        "command_name",
        existing_type=sa.VARCHAR(length=100),
        type_=sa.String(length=32),
        existing_nullable=True,
    )
    op.add_column("user", sa.Column("pending_email", sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("user", "pending_email")
    op.alter_column(
        "snippets",
        "command_name",
        existing_type=sa.String(length=32),
        type_=sa.VARCHAR(length=100),
        existing_nullable=True,
    )
    # ### end Alembic commands ###
