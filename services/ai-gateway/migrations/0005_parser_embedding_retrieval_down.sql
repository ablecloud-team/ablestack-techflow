REVOKE DELETE ON rag_source_file, rag_source_blob FROM techflow_rag_app;
REVOKE INSERT, UPDATE, DELETE ON rag_chunk, rag_chunk_embedding, rag_code_symbol, rag_code_relation FROM techflow_rag_app;

DROP INDEX IF EXISTS rag_provider_call_ingestion_idx;
ALTER TABLE rag_provider_call DROP CONSTRAINT IF EXISTS rag_provider_call_subject_check;
ALTER TABLE rag_provider_call ADD CONSTRAINT rag_provider_call_check
    CHECK (query_id IS NOT NULL OR evaluation_run_id IS NOT NULL);
ALTER TABLE rag_provider_call DROP COLUMN IF EXISTS ingestion_job_id;

ALTER TABLE rag_ingestion_job DROP COLUMN IF EXISTS metrics;
ALTER TABLE rag_ingestion_job DROP COLUMN IF EXISTS completed_at;
ALTER TABLE rag_ingestion_job DROP COLUMN IF EXISTS started_at;
ALTER TABLE rag_ingestion_job DROP COLUMN IF EXISTS execution_idempotency_key;

DROP INDEX IF EXISTS rag_chunk_path_active_idx;
ALTER TABLE rag_chunk DROP COLUMN IF EXISTS token_count;
ALTER TABLE rag_chunk DROP COLUMN IF EXISTS chunk_index;
ALTER TABLE rag_chunk DROP COLUMN IF EXISTS parser_profile_id;
