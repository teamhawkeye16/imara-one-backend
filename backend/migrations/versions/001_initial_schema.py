"""Initial schema for IMARA ONE Search

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-11-16 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. domains
    op.create_table(
        'domains',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('domain_name', sa.String(length=255), nullable=False),
        sa.Column('is_allowed', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('robots_txt', sa.Text(), nullable=True),
        sa.Column('crawl_frequency_hours', sa.Integer(), nullable=False, server_default='24'),
        sa.Column('last_crawled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('domain_name')
    )
    op.create_index('ix_domains_domain_name', 'domains', ['domain_name'])
    op.create_index('ix_domains_is_allowed', 'domains', ['is_allowed'])

    # 2. documents
    op.create_table(
        'documents',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('domain_id', sa.String(length=36), nullable=False),
        sa.Column('url', sa.Text(), nullable=False),
        sa.Column('canonical_url', sa.Text(), nullable=True),
        sa.Column('title', sa.String(length=512), nullable=False),
        sa.Column('meta_description', sa.Text(), nullable=True),
        sa.Column('raw_content', sa.Text(), nullable=True),
        sa.Column('clean_text', sa.Text(), nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('language', sa.String(length=16), nullable=False, server_default='en'),
        sa.Column('http_status', sa.Integer(), nullable=False, server_default='200'),
        sa.Column('word_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('indexed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['domain_id'], ['domains.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('url')
    )
    op.create_index('ix_documents_domain_id', 'documents', ['domain_id'])
    op.create_index('ix_documents_content_hash', 'documents', ['content_hash'])
    op.create_index('ix_documents_indexed_at', 'documents', ['indexed_at'])

    # 3. document_versions
    op.create_table(
        'document_versions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('document_id', sa.String(length=36), nullable=False),
        sa.Column('version_num', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('title', sa.String(length=512), nullable=False),
        sa.Column('clean_text', sa.Text(), nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_document_versions_document_id', 'document_versions', ['document_id'])

    # 4. crawl_jobs
    op.create_table(
        'crawl_jobs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('domain_id', sa.String(length=36), nullable=True),
        sa.Column('target_url', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='pending'),
        sa.Column('pages_crawled', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('pages_indexed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('errors_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('config_json', sa.Text(), nullable=True),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['domain_id'], ['domains.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_crawl_jobs_domain_id', 'crawl_jobs', ['domain_id'])
    op.create_index('ix_crawl_jobs_status', 'crawl_jobs', ['status'])

    # 5. crawl_pages
    op.create_table(
        'crawl_pages',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('job_id', sa.String(length=36), nullable=False),
        sa.Column('url', sa.Text(), nullable=False),
        sa.Column('status_code', sa.Integer(), nullable=True),
        sa.Column('content_hash', sa.String(length=64), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('discovered_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['job_id'], ['crawl_jobs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_crawl_pages_job_id', 'crawl_pages', ['job_id'])

    # 6. search_queries
    op.create_table(
        'search_queries',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('query_hash', sa.String(length=64), nullable=False),
        sa.Column('query_length', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('results_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('response_time_ms', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('has_results', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_search_queries_query_hash', 'search_queries', ['query_hash'])
    op.create_index('ix_search_queries_created_at', 'search_queries', ['created_at'])

    # 7. search_results
    op.create_table(
        'search_results',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('query_hash', sa.String(length=64), nullable=False),
        sa.Column('document_id', sa.String(length=36), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('relevance_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_search_results_query_hash', 'search_results', ['query_hash'])
    op.create_index('ix_search_results_document_id', 'search_results', ['document_id'])

    # 8. ai_answers
    op.create_table(
        'ai_answers',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('query_hash', sa.String(length=64), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('answer_text', sa.Text(), nullable=False),
        sa.Column('provider', sa.String(length=64), nullable=False, server_default='ollama'),
        sa.Column('model_used', sa.String(length=64), nullable=False, server_default='llama3.2'),
        sa.Column('generation_time_ms', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_ai_answers_query_hash', 'ai_answers', ['query_hash'])

    # 9. answer_citations
    op.create_table(
        'answer_citations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('answer_id', sa.String(length=36), nullable=False),
        sa.Column('document_id', sa.String(length=36), nullable=True),
        sa.Column('url', sa.Text(), nullable=False),
        sa.Column('title', sa.String(length=512), nullable=False, server_default=''),
        sa.Column('snippet', sa.Text(), nullable=False),
        sa.Column('relevance_score', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['answer_id'], ['ai_answers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_answer_citations_answer_id', 'answer_citations', ['answer_id'])
    op.create_index('ix_answer_citations_document_id', 'answer_citations', ['document_id'])

    # 10. user_settings
    op.create_table(
        'user_settings',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('client_id_hash', sa.String(length=64), nullable=False),
        sa.Column('safe_search', sa.String(length=16), nullable=False, server_default='moderate'),
        sa.Column('privacy_level', sa.String(length=16), nullable=False, server_default='maximum'),
        sa.Column('ai_enabled', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('results_per_page', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('theme', sa.String(length=16), nullable=False, server_default='dark'),
        sa.Column('allow_anonymous_metrics', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('client_id_hash')
    )
    op.create_index('ix_user_settings_client_id_hash', 'user_settings', ['client_id_hash'])

    # 11. security_events
    op.create_table(
        'security_events',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('event_type', sa.String(length=64), nullable=False),
        sa.Column('severity', sa.String(length=16), nullable=False, server_default='warning'),
        sa.Column('client_ip_hash', sa.String(length=64), nullable=False),
        sa.Column('endpoint', sa.String(length=255), nullable=False),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_security_events_event_type', 'security_events', ['event_type'])
    op.create_index('ix_security_events_client_ip_hash', 'security_events', ['client_ip_hash'])
    op.create_index('ix_security_events_created_at', 'security_events', ['created_at'])


def downgrade() -> None:
    op.drop_table('security_events')
    op.drop_table('user_settings')
    op.drop_table('answer_citations')
    op.drop_table('ai_answers')
    op.drop_table('search_results')
    op.drop_table('search_queries')
    op.drop_table('crawl_pages')
    op.drop_table('crawl_jobs')
    op.drop_table('document_versions')
    op.drop_table('documents')
    op.drop_table('domains')

