"""Add repo fields to workspaces table.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-03
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("workspaces", schema=None) as batch_op:
        batch_op.add_column(sa.Column("repo_url", sa.String(500), nullable=True))
        batch_op.add_column(
            sa.Column("repo_branch", sa.String(255), nullable=True, server_default="main")
        )
        batch_op.add_column(sa.Column("repo_auth_secret", sa.String(255), nullable=True))
        batch_op.add_column(sa.Column("last_synced_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("sync_status", sa.String(50), nullable=True))
        batch_op.add_column(sa.Column("sync_error", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("workspaces", schema=None) as batch_op:
        batch_op.drop_column("sync_error")
        batch_op.drop_column("sync_status")
        batch_op.drop_column("last_synced_at")
        batch_op.drop_column("repo_auth_secret")
        batch_op.drop_column("repo_branch")
        batch_op.drop_column("repo_url")
