"""Initial schema - chat sessions, messages, usage, and events

Revision ID: 001
Revises: 
Create Date: 2026-01-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create chat_sessions table
    op.create_table(
        'chat_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('model_name', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create chat_messages table
    op.create_table(
        'chat_messages',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('chat_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('role', sa.String(50), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('message_metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['chat_id'], ['chat_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create chat_usage table
    op.create_table(
        'chat_usage',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('chat_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('input_tokens', sa.Integer(), nullable=False),
        sa.Column('output_tokens', sa.Integer(), nullable=False),
        sa.Column('total_tokens', sa.Integer(), nullable=False),
        sa.Column('cost_usd', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['chat_id'], ['chat_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create chat_events table
    op.create_table(
        'chat_events',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('chat_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('message_id', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('event_name', sa.String(255), nullable=True),
        sa.Column('event_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['chat_id'], ['chat_sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['message_id'], ['chat_messages.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for common queries
    op.create_index('ix_chat_messages_chat_id', 'chat_messages', ['chat_id'])
    op.create_index('ix_chat_usage_chat_id', 'chat_usage', ['chat_id'])
    op.create_index('ix_chat_events_chat_id', 'chat_events', ['chat_id'])
    op.create_index('ix_chat_events_message_id', 'chat_events', ['message_id'])
    op.create_index('ix_chat_events_event_type', 'chat_events', ['event_type'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_chat_events_event_type', table_name='chat_events')
    op.drop_index('ix_chat_events_message_id', table_name='chat_events')
    op.drop_index('ix_chat_events_chat_id', table_name='chat_events')
    op.drop_index('ix_chat_usage_chat_id', table_name='chat_usage')
    op.drop_index('ix_chat_messages_chat_id', table_name='chat_messages')
    
    # Drop tables in reverse order (respecting foreign keys)
    op.drop_table('chat_events')
    op.drop_table('chat_usage')
    op.drop_table('chat_messages')
    op.drop_table('chat_sessions')
