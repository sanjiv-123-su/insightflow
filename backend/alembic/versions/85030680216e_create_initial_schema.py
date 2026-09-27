"""create_initial_schema

Revision ID: 85030680216e
Revises: 
Create Date: 2026-09-27 17:11:36.472366

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '85030680216e'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: Create initial InsightFlow PostgreSQL tables."""
    # 1. users
    op.create_table(
        'users',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_users')),
        sa.UniqueConstraint('email', name=op.f('uq_users_email')),
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # 2. datasets
    op.create_table(
        'datasets',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('file_type', sa.String(length=50), nullable=False),
        sa.Column('file_size', sa.BigInteger(), nullable=False),
        sa.Column('row_count', sa.BigInteger(), nullable=True),
        sa.Column('column_count', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=50), server_default='pending', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('file_size >= 0', name='ck_datasets_file_size_positive'),
        sa.CheckConstraint('row_count IS NULL OR row_count >= 0', name='ck_datasets_row_count_positive'),
        sa.CheckConstraint('column_count IS NULL OR column_count >= 0', name='ck_datasets_column_count_positive'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_datasets_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_datasets')),
    )
    op.create_index(op.f('ix_datasets_user_id'), 'datasets', ['user_id'], unique=False)
    op.create_index(op.f('ix_datasets_name'), 'datasets', ['name'], unique=False)
    op.create_index(op.f('ix_datasets_status'), 'datasets', ['status'], unique=False)
    op.create_index('ix_datasets_user_id_created_at', 'datasets', ['user_id', 'created_at'], unique=False)

    # 3. dataset_columns
    op.create_table(
        'dataset_columns',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('dataset_id', sa.Uuid(), nullable=False),
        sa.Column('column_name', sa.String(length=255), nullable=False),
        sa.Column('data_type', sa.String(length=100), nullable=False),
        sa.Column('nullable', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('null_count', sa.BigInteger(), server_default=sa.text('0'), nullable=False),
        sa.Column('unique_count', sa.BigInteger(), server_default=sa.text('0'), nullable=False),
        sa.CheckConstraint('null_count >= 0', name='ck_dataset_columns_null_count_positive'),
        sa.CheckConstraint('unique_count >= 0', name='ck_dataset_columns_unique_count_positive'),
        sa.ForeignKeyConstraint(['dataset_id'], ['datasets.id'], name=op.f('fk_dataset_columns_dataset_id_datasets'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_dataset_columns')),
        sa.UniqueConstraint('dataset_id', 'column_name', name='uq_dataset_columns_dataset_colname'),
    )
    op.create_index(op.f('ix_dataset_columns_dataset_id'), 'dataset_columns', ['dataset_id'], unique=False)

    # 4. data_quality_reports
    op.create_table(
        'data_quality_reports',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('dataset_id', sa.Uuid(), nullable=False),
        sa.Column('missing_values', sa.BigInteger(), server_default=sa.text('0'), nullable=False),
        sa.Column('duplicate_rows', sa.BigInteger(), server_default=sa.text('0'), nullable=False),
        sa.Column('invalid_values', sa.BigInteger(), server_default=sa.text('0'), nullable=False),
        sa.Column('quality_score', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('missing_values >= 0', name='ck_data_quality_missing_values_positive'),
        sa.CheckConstraint('duplicate_rows >= 0', name='ck_data_quality_duplicate_rows_positive'),
        sa.CheckConstraint('invalid_values >= 0', name='ck_data_quality_invalid_values_positive'),
        sa.CheckConstraint('quality_score >= 0.0 AND quality_score <= 100.0', name='ck_data_quality_score_range'),
        sa.ForeignKeyConstraint(['dataset_id'], ['datasets.id'], name=op.f('fk_data_quality_reports_dataset_id_datasets'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_data_quality_reports')),
    )
    op.create_index(op.f('ix_data_quality_reports_dataset_id'), 'data_quality_reports', ['dataset_id'], unique=False)
    op.create_index('ix_data_quality_reports_dataset_id_created_at', 'data_quality_reports', ['dataset_id', 'created_at'], unique=False)

    # 5. saved_queries
    op.create_table(
        'saved_queries',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('dataset_id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('query', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['dataset_id'], ['datasets.id'], name=op.f('fk_saved_queries_dataset_id_datasets'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_saved_queries_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_saved_queries')),
    )
    op.create_index(op.f('ix_saved_queries_user_id'), 'saved_queries', ['user_id'], unique=False)
    op.create_index(op.f('ix_saved_queries_dataset_id'), 'saved_queries', ['dataset_id'], unique=False)
    op.create_index('ix_saved_queries_user_id_dataset_id', 'saved_queries', ['user_id', 'dataset_id'], unique=False)

    # 6. analytics_results
    op.create_table(
        'analytics_results',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('dataset_id', sa.Uuid(), nullable=False),
        sa.Column('analysis_type', sa.String(length=100), nullable=False),
        sa.Column('result', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['dataset_id'], ['datasets.id'], name=op.f('fk_analytics_results_dataset_id_datasets'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_analytics_results')),
    )
    op.create_index(op.f('ix_analytics_results_dataset_id'), 'analytics_results', ['dataset_id'], unique=False)
    op.create_index(op.f('ix_analytics_results_analysis_type'), 'analytics_results', ['analysis_type'], unique=False)
    op.create_index('ix_analytics_results_dataset_id_analysis_type', 'analytics_results', ['dataset_id', 'analysis_type'], unique=False)
    op.create_index('ix_analytics_results_dataset_id_created_at', 'analytics_results', ['dataset_id', 'created_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema: Drop tables in reverse dependency order."""
    op.drop_table('analytics_results')
    op.drop_table('saved_queries')
    op.drop_table('data_quality_reports')
    op.drop_table('dataset_columns')
    op.drop_table('datasets')
    op.drop_table('users')
