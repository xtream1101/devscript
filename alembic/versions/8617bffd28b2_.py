"""empty message

Revision ID: 8617bffd28b2
Revises: 1497fb563015, 6979532c43d3
Create Date: 2025-01-11 03:41:35.884254

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8617bffd28b2"
down_revision: Union[str, None] = ("1497fb563015", "6979532c43d3")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
