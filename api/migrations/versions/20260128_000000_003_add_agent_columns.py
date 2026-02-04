"""Add agent_id and agent_name, remove model_name from chat_sessions

Revision ID: 003
Revises: 002
Create Date: 2026-01-28 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add agent_id column
    op.add_column(
        'chat_sessions',
        sa.Column('agent_id', sa.String(100), nullable=True, server_default='hello-world')
    )
    
    # Add agent_name column
    op.add_column(
        'chat_sessions',
        sa.Column('agent_name', sa.String(255), nullable=True)
    )
    
    # Migrate existing data: copy model_name to agent_id for existing sessions
    op.execute("""
        UPDATE chat_sessions 
        SET agent_id = model_name 
        WHERE model_name IS NOT NULL AND agent_id IS NULL
    """)
    
    # Drop the legacy model_name column
    op.drop_column('chat_sessions', 'model_name')


def downgrade() -> None:
    # Re-add model_name column
    op.add_column(
        'chat_sessions',
        sa.Column('model_name', sa.String(100), nullable=True, server_default='gpt-4o')
    )
    
    # Copy agent_id back to model_name
    op.execute("""
        UPDATE chat_sessions 
        SET model_name = agent_id 
        WHERE agent_id IS NOT NULL
    """)
    
    op.drop_column('chat_sessions', 'agent_name')
    op.drop_column('chat_sessions', 'agent_id')
