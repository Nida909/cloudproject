"""Add directory_id column to file table

Revision ID: ddade64986d2
Revises: fe11d1a9d91b
Create Date: 2024-03-11 21:57:25.502381

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ddade64986d2'
down_revision = 'fe11d1a9d91b'
branch_labels = None
depends_on = None


def upgrade():
    # Add the directory_id column to the file table
    op.add_column('file', sa.Column('directory_id', sa.Integer(), nullable=True))


def downgrade():
    # Drop the directory_id column from the file table if needed
    op.drop_column('file', 'directory_id')


    # ### end Alembic commands ###
