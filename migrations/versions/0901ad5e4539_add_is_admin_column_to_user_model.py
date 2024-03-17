"""Add is_admin column to User model

Revision ID: 0901ad5e4539
Revises: ddade64986d2
Create Date: 2024-03-13 15:26:31.306660

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0901ad5e4539'
down_revision = 'ddade64986d2'
branch_labels = None
depends_on = None


def upgrade():
    # Add the is_admin column to the user table
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_admin', sa.Boolean(), nullable=True))

    # Add a named constraint for the foreign key
    with op.batch_alter_table('file', schema=None) as batch_op:
        batch_op.create_foreign_key('fk_user_id', 'user', ['user_id'], ['id'])

def downgrade():
    # Drop the is_admin column from the user table
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('is_admin')

    # Drop the named constraint for the foreign key
    with op.batch_alter_table('file', schema=None) as batch_op:
        batch_op.drop_constraint('fk_user_id', type_='foreignkey')


    # ### end Alembic commands ###
