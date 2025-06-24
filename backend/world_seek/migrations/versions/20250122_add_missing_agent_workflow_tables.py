"""add missing agent and workflow_app tables

Revision ID: 20250122_missing_tables
Revises: 3781e22d8b01
Create Date: 2025-01-22 10:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

import world_seek.internal.db
from world_seek.internal.db import JSONField
from world_seek.migrations.util import get_existing_tables

# revision identifiers, used by Alembic.
revision: str = "20250122_missing_tables"
down_revision: Union[str, None] = "3781e22d8b01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    existing_tables = set(get_existing_tables())

    # 创建 agent 表
    if "agent" not in existing_tables:
        op.create_table(
            "agent",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Text(), nullable=True),
            sa.Column("base_app_id", sa.Integer(), nullable=True),
            sa.Column("name", sa.Text(), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("params", JSONField(), nullable=True),
            sa.Column("access_control", sa.JSON(), nullable=True),
            sa.Column("is_deleted", sa.Boolean(), nullable=True, default=False),
            sa.Column("updated_at", sa.BigInteger(), nullable=True),
            sa.Column("created_at", sa.BigInteger(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )

    # 创建 workflow_app 表
    if "workflow_app" not in existing_tables:
        op.create_table(
            "workflow_app",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.Text(), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("params", JSONField(), nullable=True),
            sa.Column("app_token", sa.Text(), nullable=True),
            sa.Column("api_path", sa.Text(), nullable=True),
            sa.Column("is_deleted", sa.Boolean(), nullable=True, default=False),
            sa.Column("updated_at", sa.BigInteger(), nullable=True),
            sa.Column("created_at", sa.BigInteger(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )


def downgrade() -> None:
    # 删除表的顺序与创建相反
    op.drop_table("workflow_app")
    op.drop_table("agent") 