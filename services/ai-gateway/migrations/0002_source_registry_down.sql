-- Destructive Issue #42 rollback. Run only after disabling discovery and indexing.

DROP TABLE IF EXISTS rag_source_scan_finding;
DROP TABLE IF EXISTS rag_source_file;
DROP TABLE IF EXISTS rag_source_blob;

ALTER TABLE rag_ingestion_job DROP COLUMN IF EXISTS completion_idempotency_key;

UPDATE rag_source_version SET state = 'QUARANTINED' WHERE state IN ('REGISTERED', 'APPROVED', 'INDEXING');
UPDATE rag_source SET state = 'QUARANTINED' WHERE state IN ('REGISTERED', 'APPROVED', 'INDEXING');

ALTER TABLE rag_source_version DROP CONSTRAINT IF EXISTS rag_source_version_state_check;
ALTER TABLE rag_source_version ADD CONSTRAINT rag_source_version_state_check
    CHECK (state IN ('QUARANTINED', 'ACTIVE', 'WITHDRAWN', 'REJECTED'));
ALTER TABLE rag_source DROP CONSTRAINT IF EXISTS rag_source_state_check;
ALTER TABLE rag_source ADD CONSTRAINT rag_source_state_check
    CHECK (state IN ('QUARANTINED', 'ACTIVE', 'WITHDRAWN'));

ALTER TABLE rag_source_version DROP COLUMN IF EXISTS indexed_file_count;
ALTER TABLE rag_source_version DROP COLUMN IF EXISTS quarantine_exclusions_accepted;
ALTER TABLE rag_source_version DROP COLUMN IF EXISTS blocking_violation_count;
ALTER TABLE rag_source_version DROP COLUMN IF EXISTS excluded_file_count;
ALTER TABLE rag_source_version DROP COLUMN IF EXISTS scanned_at;
ALTER TABLE rag_source_version DROP COLUMN IF EXISTS scan_idempotency_key;
ALTER TABLE rag_source_version DROP COLUMN IF EXISTS scanned_by;
ALTER TABLE rag_source_version DROP COLUMN IF EXISTS detected_by;
ALTER TABLE rag_source_version DROP COLUMN IF EXISTS snapshot_hash;
ALTER TABLE rag_source_version DROP COLUMN IF EXISTS tree_sha;

ALTER TABLE rag_source DROP COLUMN IF EXISTS license_metadata;
ALTER TABLE rag_source DROP COLUMN IF EXISTS initial_reviewer;
ALTER TABLE rag_source DROP COLUMN IF EXISTS retention_policy;
ALTER TABLE rag_source DROP COLUMN IF EXISTS owner;
