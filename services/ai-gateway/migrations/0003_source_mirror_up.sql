BEGIN;

CREATE TABLE rag_source_mirror (
    repository text PRIMARY KEY,
    mirror_key text NOT NULL UNIQUE,
    state text NOT NULL DEFAULT 'UNINITIALIZED'
        CHECK (state IN ('UNINITIALIZED', 'HEALTHY', 'DEGRADED', 'STALE')),
    sync_policy text NOT NULL DEFAULT 'SCHEDULE_6H_RECONCILIATION',
    stale_after_seconds integer NOT NULL DEFAULT 86400 CHECK (stale_after_seconds >= 3600),
    last_attempt_at timestamptz,
    last_success_at timestamptz,
    last_head_commit char(40),
    last_error_code text,
    consecutive_failures integer NOT NULL DEFAULT 0 CHECK (consecutive_failures >= 0),
    last_duration_ms integer CHECK (last_duration_ms IS NULL OR last_duration_ms >= 0),
    updated_at timestamptz NOT NULL DEFAULT now()
);

INSERT INTO rag_source_mirror (repository, mirror_key) VALUES
    ('ablecloud-team/ablestack-cloud', 'ablecloud-team__ablestack-cloud.git'),
    ('ablecloud-team/ablestack-cockpit-plugin', 'ablecloud-team__ablestack-cockpit-plugin.git'),
    ('ablecloud-team/ablestack-docs', 'ablecloud-team__ablestack-docs.git'),
    ('ablecloud-team/ablestack-genie', 'ablecloud-team__ablestack-genie.git'),
    ('ablecloud-team/ablestack-kickstart', 'ablecloud-team__ablestack-kickstart.git'),
    ('ablecloud-team/ablestack-qemu-exec-tools', 'ablecloud-team__ablestack-qemu-exec-tools.git'),
    ('ablecloud-team/ablestack-wall', 'ablecloud-team__ablestack-wall.git');

GRANT SELECT, INSERT, UPDATE ON rag_source_mirror TO techflow_rag_app;
GRANT SELECT, INSERT, UPDATE ON rag_source_mirror TO techflow_rag_source_fetcher;

COMMIT;
