"""Add session_id field to chat table

Revision ID: 20250123_add_session_id
Revises: 20250122_missing_tables
Create Date: 2025-01-23 10:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20250123_add_session_id"
down_revision: Union[str, None] = "20250122_missing_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


import uuid

def upgrade() -> None:
    """Add session_id column to chat table"""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = inspector.get_columns("chat")
    column_names = [col["name"] for col in columns]

    if "session_id" not in column_names:
        print("Adding session_id column to chat table (using batch mode for SQLite)")

        # Step 1: Add the column as nullable
        op.add_column("chat", sa.Column("session_id", sa.String(), nullable=True))

        # Step 2: Populate existing rows with a default UUID value
        print("Populating existing rows with default session_id")
        chat_table = sa.table('chat',
                              sa.column('id', sa.String),
                              sa.column('session_id', sa.String))
        
        rows = conn.execute(sa.text("SELECT id FROM chat WHERE session_id IS NULL")).fetchall()
        for row in rows:
            chat_id = row[0]
            op.execute(
                chat_table.update().where(chat_table.c.id == chat_id).values(session_id=str(uuid.uuid4()))
            )

        # Step 3: Use batch mode to alter the column to be non-nullable,
        # which is required for SQLite compatibility.
        print("Altering column to be non-nullable using batch mode")
        with op.batch_alter_table("chat", schema=None) as batch_op:
            batch_op.alter_column("session_id",
                                  existing_type=sa.String(),
                                  nullable=False)

    else:
        print("session_id column already exists in chat table.")
        # Even if the column exists, we need to ensure all values are populated before making it non-nullable.
        rows = conn.execute(sa.text("SELECT id FROM chat WHERE session_id IS NULL")).fetchall()
        if rows:
            print(f"Found {len(rows)} rows with NULL session_id. Populating them.")
            chat_table = sa.table('chat', sa.column('id', sa.String), sa.column('session_id', sa.String))
            for row in rows:
                chat_id = row[0]
                op.execute(
                    chat_table.update().where(chat_table.c.id == chat_id).values(session_id=str(uuid.uuid4()))
                )
        
            print("Altering column to be non-nullable using batch mode")
            with op.batch_alter_table("chat", schema=None) as batch_op:
                batch_op.alter_column('session_id',
                                      existing_type=sa.VARCHAR(),
                                      nullable=False)
        else:
            print("No rows with NULL session_id found.")


def downgrade() -> None:
    """Remove session_id column from chat table"""
    # 检查session_id列是否存在，如果存在则删除
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    columns = inspector.get_columns("chat")
    column_names = [col["name"] for col in columns]
    
    if "session_id" in column_names:
        print("Removing session_id column from chat table")
        op.drop_column("chat", "session_id")
    else:
        print("session_id column does not exist in chat table") 