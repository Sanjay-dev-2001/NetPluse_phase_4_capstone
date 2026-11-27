"""Create devices and alerts tables.

Revision ID: 0f31d72c49a1
Revises:
"""

from alembic import op
import sqlalchemy as sa

revision = "0f31d72c49a1"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "devices",
        sa.Column("device_id", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("device_type", sa.String(length=50), nullable=False),
        sa.Column("ip_address", sa.String(length=45), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("device_id"),
    )
    op.create_index(op.f("ix_devices_device_id"), "devices", ["device_id"], unique=False)
    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("device_id", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["device_id"], ["devices.device_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_alerts_device_id"), "alerts", ["device_id"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_alerts_device_id"), table_name="alerts")
    op.drop_table("alerts")
    op.drop_index(op.f("ix_devices_device_id"), table_name="devices")
    op.drop_table("devices")