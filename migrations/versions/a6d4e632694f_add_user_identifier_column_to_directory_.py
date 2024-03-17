from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a6d4e632694f'
down_revision = '90f55dbb5d9c'
branch_labels = None
depends_on = None

def upgrade():
    # Check if the column already exists
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = inspector.get_columns('directory')
    column_names = [column['name'] for column in columns]
    if 'user_identifier' not in column_names:
        # Add the user_identifier column with a default value
        op.add_column('directory', sa.Column('user_identifier', sa.String(length=50), nullable=False, server_default=''))

        # Update existing rows
        meta = sa.MetaData(bind=connection)
        directory = sa.Table('directory', meta, autoload=True)
        connection.execute(directory.update().values(user_identifier=''))

def downgrade():
    # Remove the user_identifier column
    op.drop_column('directory', 'user_identifier')
