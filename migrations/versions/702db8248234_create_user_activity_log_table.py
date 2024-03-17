from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = '702db8248234'
down_revision = '0901ad5e4539'
branch_labels = None
depends_on = None

def table_exists(table_name):
    insp = Inspector.from_engine(op.get_bind())
    return table_name in insp.get_table_names()

def upgrade():
    if not table_exists('user_activity_log'):
        op.create_table(
            'user_activity_log',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('activity', sa.String(length=255), nullable=False),
            sa.Column('timestamp', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
            sa.PrimaryKeyConstraint('id')
        )

def downgrade():
    op.drop_table('user_activity_log')
