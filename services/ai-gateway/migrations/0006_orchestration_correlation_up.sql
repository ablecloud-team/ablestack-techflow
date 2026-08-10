-- TechFlow AI Gateway Issue #45: correlate Activepieces flow runs with jobs and evaluations.

ALTER TABLE rag_ingestion_job ADD COLUMN IF NOT EXISTS correlation_id varchar(128);
UPDATE rag_ingestion_job
SET correlation_id = 'legacy-job-' || left(id::text, 36)
WHERE correlation_id IS NULL;
ALTER TABLE rag_ingestion_job ALTER COLUMN correlation_id SET NOT NULL;
CREATE INDEX IF NOT EXISTS rag_ingestion_job_correlation_idx
    ON rag_ingestion_job (correlation_id, created_at DESC);

ALTER TABLE rag_evaluation_run ADD COLUMN IF NOT EXISTS correlation_id varchar(128);
UPDATE rag_evaluation_run
SET correlation_id = 'legacy-evaluation-' || left(id::text, 36)
WHERE correlation_id IS NULL;
ALTER TABLE rag_evaluation_run ALTER COLUMN correlation_id SET NOT NULL;
CREATE INDEX IF NOT EXISTS rag_evaluation_run_correlation_idx
    ON rag_evaluation_run (correlation_id, created_at DESC);
