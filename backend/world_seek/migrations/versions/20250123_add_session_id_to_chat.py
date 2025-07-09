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


def upgrade() -> None:
    """Add session_id column to chat table"""
    # 检查chat表是否存在session_id列
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # 获取chat表的所有列
    columns = inspector.get_columns("chat")
    column_names = [col["name"] for col in columns]
    
    # 如果session_id列不存在，则添加它
    if "session_id" not in column_names:
        print("Adding session_id column to chat table")
        op.add_column("chat", sa.Column("session_id", sa.String(), nullable=False))
    else:
        print("session_id column already exists in chat table")


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