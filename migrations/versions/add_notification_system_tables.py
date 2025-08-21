"""Add notification system tables

Revision ID: add_notification_system
Revises: 
Create Date: 2025-08-20 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_notification_system'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create notifications table
    op.create_table('notifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False, comment='通知类型: twitter, solana, system'),
        sa.Column('title', sa.String(length=200), nullable=False, comment='通知标题'),
        sa.Column('content', sa.Text(), nullable=False, comment='通知内容'),
        sa.Column('status', sa.String(length=20), nullable=True, comment='通知状态: pending, sent, failed'),
        sa.Column('is_urgent', sa.Boolean(), nullable=True, comment='是否紧急通知'),
        sa.Column('channel', sa.String(length=50), nullable=True, comment='通知渠道: wechat, email, sms'),
        sa.Column('related_type', sa.String(length=50), nullable=True, comment='关联数据类型'),
        sa.Column('related_id', sa.String(length=100), nullable=True, comment='关联数据ID'),
        sa.Column('data', sa.JSON(), nullable=True, comment='扩展数据'),
        sa.Column('sent_at', sa.DateTime(), nullable=True, comment='发送时间'),
        sa.Column('error_message', sa.Text(), nullable=True, comment='错误信息'),
        sa.Column('retry_count', sa.Integer(), nullable=True, comment='重试次数'),
        sa.Column('dedup_key', sa.String(length=255), nullable=True, comment='去重键'),
        sa.Column('created_at', sa.DateTime(), nullable=True, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=True, comment='更新时间'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notifications_id'), 'notifications', ['id'], unique=False)
    op.create_index(op.f('ix_notifications_dedup_key'), 'notifications', ['dedup_key'], unique=False)

    # Create notification_templates table
    op.create_table('notification_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False, comment='模板名称'),
        sa.Column('type', sa.String(length=50), nullable=False, comment='通知类型'),
        sa.Column('title_template', sa.String(length=200), nullable=False, comment='标题模板'),
        sa.Column('content_template', sa.Text(), nullable=False, comment='内容模板'),
        sa.Column('is_active', sa.Boolean(), nullable=True, comment='是否启用'),
        sa.Column('is_urgent', sa.Boolean(), nullable=True, comment='是否紧急模板'),
        sa.Column('channel', sa.String(length=50), nullable=True, comment='默认通知渠道'),
        sa.Column('dedup_enabled', sa.Boolean(), nullable=True, comment='是否启用去重'),
        sa.Column('dedup_window_seconds', sa.Integer(), nullable=True, comment='去重时间窗口(秒)'),
        sa.Column('variables', sa.JSON(), nullable=True, comment='模板变量说明'),
        sa.Column('created_at', sa.DateTime(), nullable=True, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=True, comment='更新时间'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notification_templates_id'), 'notification_templates', ['id'], unique=False)
    op.create_index(op.f('ix_notification_templates_name'), 'notification_templates', ['name'], unique=True)

    # Create notification_rules table
    op.create_table('notification_rules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False, comment='规则名称'),
        sa.Column('type', sa.String(length=50), nullable=False, comment='监控类型: twitter, solana'),
        sa.Column('conditions', sa.JSON(), nullable=False, comment='触发条件JSON'),
        sa.Column('template_name', sa.String(length=100), nullable=False, comment='使用的模板名称'),
        sa.Column('is_active', sa.Boolean(), nullable=True, comment='是否启用'),
        sa.Column('priority', sa.Integer(), nullable=True, comment='优先级，数字越大优先级越高'),
        sa.Column('rate_limit_enabled', sa.Boolean(), nullable=True, comment='是否启用限流'),
        sa.Column('rate_limit_count', sa.Integer(), nullable=True, comment='限流次数'),
        sa.Column('rate_limit_window_seconds', sa.Integer(), nullable=True, comment='限流时间窗口(秒)'),
        sa.Column('created_at', sa.DateTime(), nullable=True, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=True, comment='更新时间'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notification_rules_id'), 'notification_rules', ['id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_notification_rules_id'), table_name='notification_rules')
    op.drop_table('notification_rules')
    op.drop_index(op.f('ix_notification_templates_name'), table_name='notification_templates')
    op.drop_index(op.f('ix_notification_templates_id'), table_name='notification_templates')
    op.drop_table('notification_templates')
    op.drop_index(op.f('ix_notifications_dedup_key'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_id'), table_name='notifications')
    op.drop_table('notifications')