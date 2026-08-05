-- TechFlow AI Gateway Issue #43: deterministic parsing, embedding audit, retrieval and deletion execution.

ALTER TABLE rag_chunk ADD COLUMN IF NOT EXISTS parser_profile_id varchar(64) NOT NULL DEFAULT 'TREE_SITTER_V1';
ALTER TABLE rag_chunk ADD COLUMN IF NOT EXISTS chunk_index integer NOT NULL DEFAULT 0 CHECK (chunk_index >= 0);
ALTER TABLE rag_chunk ADD COLUMN IF NOT EXISTS token_count integer CHECK (token_count IS NULL OR token_count >= 0);
CREATE INDEX IF NOT EXISTS rag_chunk_path_active_idx ON rag_chunk (source_version_id, path_hash, active);

ALTER TABLE rag_ingestion_job ADD COLUMN IF NOT EXISTS execution_idempotency_key varchar(128) UNIQUE;
ALTER TABLE rag_ingestion_job ADD COLUMN IF NOT EXISTS started_at timestamptz;
ALTER TABLE rag_ingestion_job ADD COLUMN IF NOT EXISTS completed_at timestamptz;
ALTER TABLE rag_ingestion_job ADD COLUMN IF NOT EXISTS metrics jsonb NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE rag_provider_call ADD COLUMN IF NOT EXISTS ingestion_job_id uuid
    REFERENCES rag_ingestion_job(id) ON DELETE SET NULL;
ALTER TABLE rag_provider_call DROP CONSTRAINT IF EXISTS rag_provider_call_check;
ALTER TABLE rag_provider_call ADD CONSTRAINT rag_provider_call_subject_check
    CHECK (num_nonnulls(query_id, evaluation_run_id, ingestion_job_id) = 1);
CREATE INDEX IF NOT EXISTS rag_provider_call_ingestion_idx
    ON rag_provider_call (ingestion_job_id, created_at DESC) WHERE ingestion_job_id IS NOT NULL;

GRANT SELECT, INSERT, UPDATE, DELETE ON
    rag_chunk, rag_chunk_embedding, rag_code_symbol, rag_code_relation
TO techflow_rag_app;
GRANT SELECT, DELETE ON rag_source_file, rag_source_blob TO techflow_rag_app;
GRANT SELECT, INSERT, UPDATE ON rag_provider_call, rag_deletion_ledger TO techflow_rag_app;

GRANT SELECT, INSERT, UPDATE, DELETE ON
    rag_chunk, rag_chunk_embedding, rag_code_symbol, rag_code_relation
TO techflow_rag_source_fetcher;
GRANT SELECT, DELETE ON rag_source_file, rag_source_blob TO techflow_rag_source_fetcher;
GRANT SELECT, INSERT, UPDATE ON rag_provider_call, rag_deletion_ledger TO techflow_rag_source_fetcher;
