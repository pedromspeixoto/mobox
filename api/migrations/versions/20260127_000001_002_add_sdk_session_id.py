"""Add sdk_session_id to chat_sessions

Revision ID: 002
Revises: 001
Create Date: 2026-01-27 00:00:01.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add sdk_session_id column to chat_sessions
    op.add_column(
        'chat_sessions',
        sa.Column('sdk_session_id', sa.String(255), nullable=True)
    )
    
    # Add index for lookups by SDK session ID
    op.create_index(
        'ix_chat_sessions_sdk_session_id',
        'chat_sessions',
        ['sdk_session_id']
    )


def downgrade() -> None:
    op.drop_index('ix_chat_sessions_sdk_session_id', table_name='chat_sessions')
    op.drop_column('chat_sessions', 'sdk_session_id')
