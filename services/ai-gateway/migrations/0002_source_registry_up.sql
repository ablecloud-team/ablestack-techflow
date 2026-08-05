-- TechFlow AI Gateway Issue #42: allowlisted source registry and scan inventory.
-- Quarantined content is never stored; only path hashes and rule identifiers remain.

ALTER TABLE rag_source ADD COLUMN IF NOT EXISTS owner varchar(128);
ALTER TABLE rag_source ADD COLUMN IF NOT EXISTS retention_policy varchar(128);
ALTER TABLE rag_source ADD COLUMN IF NOT EXISTS initial_reviewer varchar(128);
ALTER TABLE rag_source ADD COLUMN IF NOT EXISTS license_metadata jsonb NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE rag_source DROP CONSTRAINT IF EXISTS rag_source_state_check;
ALTER TABLE rag_source ADD CONSTRAINT rag_source_state_check
    CHECK (state IN ('REGISTERED', 'QUARANTINED', 'APPROVED', 'INDEXING', 'ACTIVE', 'WITHDRAWN'));

ALTER TABLE rag_source_version ADD COLUMN IF NOT EXISTS tree_sha char(40)
    CHECK (tree_sha IS NULL OR tree_sha ~ '^[0-9a-f]{40}$');
ALTER TABLE rag_source_version ADD COLUMN IF NOT EXISTS snapshot_hash char(64)
    CHECK (snapshot_hash IS NULL OR snapshot_hash ~ '^[0-9a-f]{64}$');
ALTER TABLE rag_source_version ADD COLUMN IF NOT EXISTS detected_by varchar(128);
ALTER TABLE rag_source_version ADD COLUMN IF NOT EXISTS scanned_by varchar(128);
ALTER TABLE rag_source_version ADD COLUMN IF NOT EXISTS scan_idempotency_key varchar(128) UNIQUE;
ALTER TABLE rag_source_version ADD COLUMN IF NOT EXISTS scanned_at timestamptz;
ALTER TABLE rag_source_version ADD COLUMN IF NOT EXISTS excluded_file_count integer
    CHECK (excluded_file_count IS NULL OR excluded_file_count >= 0);
ALTER TABLE rag_source_version ADD COLUMN IF NOT EXISTS blocking_violation_count integer
    CHECK (blocking_violation_count IS NULL OR blocking_violation_count >= 0);
ALTER TABLE rag_source_version ADD COLUMN IF NOT EXISTS indexed_file_count integer
    CHECK (indexed_file_count IS NULL OR indexed_file_count >= 0);
ALTER TABLE rag_source_version ADD COLUMN IF NOT EXISTS quarantine_exclusions_accepted boolean NOT NULL DEFAULT false;

ALTER TABLE rag_source_version DROP CONSTRAINT IF EXISTS rag_source_version_state_check;
ALTER TABLE rag_source_version ADD CONSTRAINT rag_source_version_state_check
    CHECK (state IN ('REGISTERED', 'QUARANTINED', 'APPROVED', 'INDEXING', 'ACTIVE', 'WITHDRAWN', 'REJECTED'));

ALTER TABLE rag_ingestion_job ADD COLUMN IF NOT EXISTS completion_idempotency_key varchar(128) UNIQUE;

CREATE TABLE rag_source_blob (
    id uuid PRIMARY KEY,
    repository varchar(255) NOT NULL CHECK (repository ~ '^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$'),
    blob_sha char(40) NOT NULL CHECK (blob_sha ~ '^[0-9a-f]{40}$'),
    content_hash char(64) NOT NULL CHECK (content_hash ~ '^[0-9a-f]{64}$'),
    size_bytes integer NOT NULL CHECK (size_bytes BETWEEN 0 AND 1048576),
    encoding varchar(32) NOT NULL CHECK (encoding = 'utf-8'),
    classification varchar(8) NOT NULL DEFAULT 'D0' CHECK (classification = 'D0'),
    content text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (repository, blob_sha)
);

CREATE TABLE rag_source_file (
    id uuid PRIMARY KEY,
    source_version_id uuid NOT NULL REFERENCES rag_source_version(id) ON DELETE CASCADE,
    path text NOT NULL,
    path_hash char(64) NOT NULL CHECK (path_hash ~ '^[0-9a-f]{64}$'),
    blob_sha char(40) CHECK (blob_sha IS NULL OR blob_sha ~ '^[0-9a-f]{40}$'),
    source_blob_id uuid REFERENCES rag_source_blob(id) ON DELETE RESTRICT,
    content_hash char(64) CHECK (content_hash IS NULL OR content_hash ~ '^[0-9a-f]{64}$'),
    size_bytes integer CHECK (size_bytes IS NULL OR size_bytes >= 0),
    source_kind varchar(32) CHECK (source_kind IS NULL OR source_kind IN ('DOCUMENTATION', 'SOURCE_CODE', 'TEST_CODE', 'BUILD_SCHEMA')),
    encoding varchar(32),
    decision varchar(32) NOT NULL CHECK (decision IN ('ELIGIBLE', 'EXCLUDED', 'QUARANTINED')),
    rule_ids varchar(64)[] NOT NULL DEFAULT '{}',
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (source_version_id, path),
    CHECK ((decision = 'ELIGIBLE' AND source_blob_id IS NOT NULL) OR (decision <> 'ELIGIBLE' AND source_blob_id IS NULL))
);
CREATE INDEX rag_source_file_version_decision_idx ON rag_source_file (source_version_id, decision);
CREATE INDEX rag_source_file_blob_idx ON rag_source_file (source_blob_id) WHERE source_blob_id IS NOT NULL;

CREATE TABLE rag_source_scan_finding (
    id uuid PRIMARY KEY,
    source_version_id uuid NOT NULL REFERENCES rag_source_version(id) ON DELETE CASCADE,
    path_hash char(64) NOT NULL CHECK (path_hash ~ '^[0-9a-f]{64}$'),
    rule_id varchar(64) NOT NULL,
    severity varchar(16) NOT NULL CHECK (severity IN ('INFO', 'BLOCKING')),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (source_version_id, path_hash, rule_id)
);
CREATE INDEX rag_source_scan_finding_version_idx ON rag_source_scan_finding (source_version_id, severity);

INSERT INTO rag_source
    (id, source_profile_id, repository, branch, source_kind, classification, license_spdx, state,
     owner, retention_policy, initial_reviewer, license_metadata)
VALUES
    ('42000000-0000-0000-0000-000000000001', 'SHARED_DOCS', 'ablecloud-team/ablestack-docs', 'master', 'DOCUMENTATION', 'D0', 'NOASSERTION', 'REGISTERED', 'ablecloud-team', 'ACTIVE_PLUS_7D_DELETION_SLA', 'dhslove', '{"source":"registry","enforcement":"record-only"}'),
    ('42000000-0000-0000-0000-000000000002', 'CLOUD_MAIN', 'ablecloud-team/ablestack-cloud', 'main', 'SOURCE_CODE', 'D0', 'Apache-2.0', 'REGISTERED', 'ablecloud-team', 'ACTIVE_PLUS_7D_DELETION_SLA', 'dhslove', '{"source":"registry","enforcement":"record-only"}'),
    ('42000000-0000-0000-0000-000000000003', 'CLOUD_DIPLO', 'ablecloud-team/ablestack-cloud', 'ablestack-diplo', 'SOURCE_CODE', 'D0', 'Apache-2.0', 'REGISTERED', 'ablecloud-team', 'ACTIVE_PLUS_7D_DELETION_SLA', 'dhslove', '{"source":"registry","enforcement":"record-only"}'),
    ('42000000-0000-0000-0000-000000000004', 'CLOUD_EUROPA', 'ablecloud-team/ablestack-cloud', 'ablestack-europa', 'SOURCE_CODE', 'D0', 'Apache-2.0', 'REGISTERED', 'ablecloud-team', 'ACTIVE_PLUS_7D_DELETION_SLA', 'dhslove', '{"source":"registry","enforcement":"record-only"}'),
    ('42000000-0000-0000-0000-000000000005', 'WALL_MAIN', 'ablecloud-team/ablestack-wall', 'main', 'SOURCE_CODE', 'D0', 'AGPL-3.0', 'REGISTERED', 'ablecloud-team', 'ACTIVE_PLUS_7D_DELETION_SLA', 'dhslove', '{"source":"registry","enforcement":"record-only"}'),
    ('42000000-0000-0000-0000-000000000006', 'COCKPIT_DIPLO', 'ablecloud-team/ablestack-cockpit-plugin', 'ablestack-diplo', 'SOURCE_CODE', 'D0', 'NOASSERTION', 'REGISTERED', 'ablecloud-team', 'ACTIVE_PLUS_7D_DELETION_SLA', 'dhslove', '{"source":"registry","enforcement":"record-only"}'),
    ('42000000-0000-0000-0000-000000000007', 'GENIE_MASTER', 'ablecloud-team/ablestack-genie', 'master', 'SOURCE_CODE', 'D0', 'NOASSERTION', 'REGISTERED', 'ablecloud-team', 'ACTIVE_PLUS_7D_DELETION_SLA', 'dhslove', '{"source":"registry","enforcement":"record-only"}'),
    ('42000000-0000-0000-0000-000000000008', 'KICKSTART_MASTER', 'ablecloud-team/ablestack-kickstart', 'master', 'SOURCE_CODE', 'D0', 'NOASSERTION', 'REGISTERED', 'ablecloud-team', 'ACTIVE_PLUS_7D_DELETION_SLA', 'dhslove', '{"source":"registry","enforcement":"record-only"}'),
    ('42000000-0000-0000-0000-000000000009', 'QEMU_EXEC_TOOLS_MAIN', 'ablecloud-team/ablestack-qemu-exec-tools', 'main', 'SOURCE_CODE', 'D0', 'NOASSERTION', 'REGISTERED', 'ablecloud-team', 'ACTIVE_PLUS_7D_DELETION_SLA', 'dhslove', '{"source":"registry","enforcement":"record-only"}')
ON CONFLICT (source_profile_id) DO UPDATE SET
    repository = EXCLUDED.repository,
    branch = EXCLUDED.branch,
    source_kind = EXCLUDED.source_kind,
    classification = EXCLUDED.classification,
    license_spdx = EXCLUDED.license_spdx,
    owner = EXCLUDED.owner,
    retention_policy = EXCLUDED.retention_policy,
    initial_reviewer = EXCLUDED.initial_reviewer,
    license_metadata = EXCLUDED.license_metadata,
    updated_at = now();

GRANT SELECT, INSERT, UPDATE ON rag_source_blob, rag_source_file, rag_source_scan_finding TO techflow_rag_app;
GRANT SELECT, INSERT, UPDATE ON rag_source_blob, rag_source_file, rag_source_scan_finding TO techflow_rag_source_fetcher;
