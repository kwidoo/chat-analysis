"""initial auth schema

Revision ID: b20b7b30a427
Revises:
Create Date: 2025-05-05 00:00:01.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision = 'b20b7b30a427'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create roles table
    op.create_table('roles',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(50), unique=True, nullable=False),
        sa.Column('description', sa.String(255)),
    )

    # Create users table
    op.create_table('users',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.Column('mfa_secret', sa.String(255), nullable=True),
        sa.Column('mfa_enabled', sa.Boolean(), default=False),
        sa.Column('metadata', sa.JSON(), nullable=True),
    )

    # Create refresh_tokens table
    op.create_table('refresh_tokens',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('revoked', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
    )

    # Create user_roles junction table
    op.create_table('user_roles',
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id')),
        sa.Column('role_id', sa.String(36), sa.ForeignKey('roles.id')),
        sa.UniqueConstraint('user_id', 'role_id', name='uq_user_role')
    )

    # Create indexes for better performance
    op.create_index('idx_user_email', 'users', ['email'])
    op.create_index('idx_refresh_token_user', 'refresh_tokens', ['user_id'])
    op.create_index('idx_refresh_token_expiry', 'refresh_tokens', ['expires_at'])
    op.create_index('idx_user_roles_user', 'user_roles', ['user_id'])
    op.create_index('idx_user_roles_role', 'user_roles', ['role_id'])


def downgrade() -> None:
    # Drop tables in reverse order of creation
    op.drop_table('user_roles')
    op.drop_table('refresh_tokens')
    op.drop_table('users')
    op.drop_table('roles')
