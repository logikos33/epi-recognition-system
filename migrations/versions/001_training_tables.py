"""Training tables

Revision ID: 001_training_tables
Revises:
Create Date: 2026-03-29

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_training_tables'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Training Projects
    op.create_table(
        'training_projects',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.VARCHAR(255), nullable=False),
        sa.Column('description', sa.TEXT(), nullable=True),
        sa.Column('target_classes', postgresql.JSONB(), nullable=False),
        sa.Column('status', sa.VARCHAR(50), server_default='draft'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'])
    )

    # Training Videos
    op.create_table(
        'training_videos',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('filename', sa.VARCHAR(255), nullable=False),
        sa.Column('storage_path', sa.TEXT(), nullable=False),
        sa.Column('duration_seconds', sa.DECIMAL(10, 2), nullable=True),
        sa.Column('frame_count', sa.INTEGER(), nullable=True),
        sa.Column('fps', sa.DECIMAL(5, 2), nullable=True),
        sa.Column('uploaded_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['project_id'], ['training_projects.id'], ondelete='CASCADE')
    )

    # Training Frames
    op.create_table(
        'training_frames',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('video_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('frame_number', sa.INTEGER(), nullable=False),
        sa.Column('storage_path', sa.TEXT(), nullable=False),
        sa.Column('is_annotated', sa.BOOLEAN(), server_default='false'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['video_id'], ['training_videos.id'], ondelete='CASCADE')
    )

    # Annotations
    op.create_table(
        'training_annotations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('frame_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('class_name', sa.VARCHAR(100), nullable=False),
        sa.Column('bbox_x', sa.DECIMAL(10, 2), nullable=False),
        sa.Column('bbox_y', sa.DECIMAL(10, 2), nullable=False),
        sa.Column('bbox_width', sa.DECIMAL(10, 2), nullable=False),
        sa.Column('bbox_height', sa.DECIMAL(10, 2), nullable=False),
        sa.Column('confidence', sa.DECIMAL(4, 3), nullable=True),
        sa.Column('is_ai_generated', sa.BOOLEAN(), server_default='false'),
        sa.Column('is_reviewed', sa.BOOLEAN(), server_default='false'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['frame_id'], ['training_frames.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'])
    )

    # Trained Models
    op.create_table(
        'trained_models',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('model_name', sa.VARCHAR(255), nullable=False),
        sa.Column('version', sa.INTEGER(), nullable=False),
        sa.Column('storage_path', sa.TEXT(), nullable=False),
        sa.Column('map50', sa.DECIMAL(4, 3), nullable=True),
        sa.Column('map75', sa.DECIMAL(4, 3), nullable=True),
        sa.Column('map50_95', sa.DECIMAL(4, 3), nullable=True),
        sa.Column('precision', sa.DECIMAL(4, 3), nullable=True),
        sa.Column('recall', sa.DECIMAL(4, 3), nullable=True),
        sa.Column('training_epochs', sa.INTEGER(), nullable=True),
        sa.Column('training_time_seconds', sa.INTEGER(), nullable=True),
        sa.Column('is_active', sa.BOOLEAN(), server_default='false'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['project_id'], ['training_projects.id'])
    )


def downgrade() -> None:
    op.drop_table('trained_models')
    op.drop_table('training_annotations')
    op.drop_table('training_frames')
    op.drop_table('training_videos')
    op.drop_table('training_projects')
