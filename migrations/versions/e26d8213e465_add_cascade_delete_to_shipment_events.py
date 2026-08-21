"""add_cascade_delete_to_shipment_events

Revision ID: e26d8213e465
Revises: e3368b1ff87d
Create Date: 2026-08-16 14:57:21.994457

"""
from collections.abc import Sequence
from typing import Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e26d8213e465'
down_revision: Union[str, Sequence[str], None] = 'e3368b1ff87d' # noqa: UP007
branch_labels: Union[str, Sequence[str], None] = None  # noqa: UP007
depends_on: Union[str, Sequence[str], None] = None # noqa: UP007


def upgrade() -> None:
    # 1. Drop the existing foreign key constraint without CASCADE
    op.drop_constraint(
        constraint_name="shipment_event_shipment_id_fkey",
        table_name="shipment_event",
        type_="foreignkey",
    )
    # 2. Re-create the foreign key with ON DELETE CASCADE
    op.create_foreign_key(
        constraint_name="shipment_event_shipment_id_fkey",
        source_table="shipment_event",
        referent_table="shipment",
        local_cols=["shipment_id"],
        remote_cols=["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    # Revert back to foreign key without CASCADE
    op.drop_constraint(
        constraint_name="shipment_event_shipment_id_fkey",
        table_name="shipment_event",
        type_="foreignkey",
    )
    op.create_foreign_key(
        constraint_name="shipment_event_shipment_id_fkey",
        source_table="shipment_event",
        referent_table="shipment",
        local_cols=["shipment_id"],
        remote_cols=["id"],
    )