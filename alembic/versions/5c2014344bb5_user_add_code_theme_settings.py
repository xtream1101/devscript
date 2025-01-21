"""User: Add code_theme settings

Revision ID: 5c2014344bb5
Revises: e1e5a2f3397a
Create Date: 2025-01-20 21:14:34.326887

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5c2014344bb5"
down_revision: Union[str, None] = "e1e5a2f3397a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("user", sa.Column("code_theme", sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("user", "code_theme")
    # ### end Alembic commands ###
