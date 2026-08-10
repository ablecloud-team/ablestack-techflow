DROP INDEX IF EXISTS rag_evaluation_run_correlation_idx;
ALTER TABLE rag_evaluation_run DROP COLUMN IF EXISTS correlation_id;

DROP INDEX IF EXISTS rag_ingestion_job_correlation_idx;
ALTER TABLE rag_ingestion_job DROP COLUMN IF EXISTS correlation_id;
