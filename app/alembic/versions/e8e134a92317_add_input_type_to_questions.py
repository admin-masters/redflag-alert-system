"""add input_type to questions

Revision ID: e8e134a92317
Revises: 5db5abf64486
Create Date: 2025-07-16 18:33:17.252157

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e8e134a92317'
down_revision: Union[str, Sequence[str], None] = '5db5abf64486'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# --- upgrade ---
def upgrade():
    input_enum = sa.Enum("radio", "checkbox", "text",
                         name="inputtype", create_type=False)
    input_enum.create(op.get_bind(), checkfirst=True)  # enum may exist

    op.add_column(
        "questions",
        sa.Column("input_type", input_enum,
                  nullable=False, server_default="radio")
    )
    op.alter_column("questions", "input_type", server_default=None)

# --- downgrade ---
def downgrade():
    op.drop_column("questions", "input_type")
    sa.Enum(name="inputtype").drop(op.get_bind(), checkfirst=False)
