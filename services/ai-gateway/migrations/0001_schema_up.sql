-- TechFlow AI Gateway Issue #41: 15 logical tables.
-- Prompt, response, authorization header, API key, and credential columns are intentionally absent.

CREATE TABLE rag_source (
    id uuid PRIMARY KEY,
    source_profile_id varchar(64) NOT NULL UNIQUE CHECK (source_profile_id ~ '^[A-Z][A-Z0-9_]{2,63}$'),
    repository varchar(255) NOT NULL CHECK (repository ~ '^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$'),
    branch varchar(128) NOT NULL,
    source_kind varchar(32) NOT NULL CHECK (source_kind IN ('DOCUMENTATION', 'SOURCE_CODE')),
    classification varchar(8) NOT NULL DEFAULT 'D0' CHECK (classification = 'D0'),
    license_spdx varchar(64),
    state varchar(32) NOT NULL CHECK (state IN ('QUARANTINED', 'ACTIVE', 'WITHDRAWN')),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE rag_source_version (
    id uuid PRIMARY KEY,
    source_id uuid NOT NULL REFERENCES rag_source(id) ON DELETE RESTRICT,
    commit_sha char(40) NOT NULL CHECK (commit_sha ~ '^[0-9a-f]{40}$'),
    state varchar(32) NOT NULL CHECK (state IN ('QUARANTINED', 'ACTIVE', 'WITHDRAWN', 'REJECTED')),
    create_idempotency_key varchar(128) NOT NULL UNIQUE,
    approval_idempotency_key varchar(128) UNIQUE,
    approved_at timestamptz,
    approved_by varchar(128),
    approval_note varchar(500),
    candidate_file_count integer CHECK (candidate_file_count IS NULL OR candidate_file_count >= 0),
    eligible_file_count integer CHECK (eligible_file_count IS NULL OR eligible_file_count >= 0),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (source_id, commit_sha)
);
CREATE INDEX rag_source_version_active_idx ON rag_source_version (source_id, created_at DESC) WHERE state = 'ACTIVE';

CREATE TABLE rag_compatibility_set (
    id uuid PRIMARY KEY,
    name varchar(128) NOT NULL,
    product varchar(64) NOT NULL CHECK (product = 'ABLESTACK'),
    product_version varchar(64) NOT NULL,
    state varchar(32) NOT NULL CHECK (state IN ('APPROVED', 'WITHDRAWN')),
    idempotency_key varchar(128) NOT NULL UNIQUE,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (name, product_version)
);

CREATE TABLE rag_compatibility_set_source (
    compatibility_set_id uuid NOT NULL REFERENCES rag_compatibility_set(id) ON DELETE CASCADE,
    source_version_id uuid NOT NULL REFERENCES rag_source_version(id) ON DELETE RESTRICT,
    required boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (compatibility_set_id, source_version_id)
);
CREATE INDEX rag_compatibility_source_version_idx ON rag_compatibility_set_source (source_version_id);

CREATE TABLE rag_ingestion_job (
    id uuid PRIMARY KEY,
    job_type varchar(32) NOT NULL CHECK (job_type IN ('INGESTION', 'DELETION', 'REINDEX')),
    source_id uuid NOT NULL REFERENCES rag_source(id) ON DELETE RESTRICT,
    source_version_id uuid NOT NULL REFERENCES rag_source_version(id) ON DELETE RESTRICT,
    state varchar(32) NOT NULL CHECK (state IN ('PENDING', 'RUNNING', 'SUCCEEDED', 'FAILED')),
    failure_class varchar(32) CHECK (failure_class IS NULL OR failure_class IN ('RETRYABLE', 'TERMINAL', 'MANUAL_REVIEW')),
    error_code varchar(64),
    requested_by varchar(128) NOT NULL,
    idempotency_key varchar(128) NOT NULL UNIQUE,
    attempt smallint NOT NULL DEFAULT 0 CHECK (attempt BETWEEN 0 AND 3),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX rag_ingestion_job_source_idx ON rag_ingestion_job (source_version_id, created_at DESC);

CREATE TABLE rag_chunk (
    id uuid PRIMARY KEY,
    source_version_id uuid NOT NULL REFERENCES rag_source_version(id) ON DELETE RESTRICT,
    source_kind varchar(32) NOT NULL CHECK (source_kind IN ('DOCUMENTATION', 'SOURCE_CODE', 'TEST_CODE', 'BUILD_SCHEMA')),
    classification varchar(8) NOT NULL DEFAULT 'D0' CHECK (classification = 'D0'),
    path text NOT NULL,
    path_hash char(64) NOT NULL CHECK (path_hash ~ '^[0-9a-f]{64}$'),
    symbol varchar(512),
    start_line integer CHECK (start_line IS NULL OR start_line > 0),
    end_line integer CHECK (end_line IS NULL OR end_line >= start_line),
    content text NOT NULL,
    content_hash char(64) NOT NULL CHECK (content_hash ~ '^[0-9a-f]{64}$'),
    parser_status varchar(32) NOT NULL CHECK (parser_status IN ('PARSED', 'FALLBACK')),
    active boolean NOT NULL DEFAULT true,
    search_document tsvector GENERATED ALWAYS AS (to_tsvector('simple', content)) STORED,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (source_version_id, path_hash, content_hash, start_line, end_line)
);
CREATE INDEX rag_chunk_source_active_idx ON rag_chunk (source_version_id, active);
CREATE INDEX rag_chunk_search_idx ON rag_chunk USING gin (search_document);
CREATE INDEX rag_chunk_symbol_trgm_idx ON rag_chunk USING gin (symbol gin_trgm_ops) WHERE symbol IS NOT NULL;

CREATE TABLE rag_embedding_profile (
    id uuid PRIMARY KEY,
    profile_id varchar(64) NOT NULL UNIQUE,
    provider varchar(32) NOT NULL CHECK (provider = 'openai'),
    model varchar(128) NOT NULL,
    dimension integer NOT NULL CHECK (dimension BETWEEN 1 AND 4096),
    profile_version integer NOT NULL CHECK (profile_version > 0),
    active boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX rag_embedding_profile_one_active_idx ON rag_embedding_profile (active) WHERE active;

INSERT INTO rag_embedding_profile (id, profile_id, provider, model, dimension, profile_version, active)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'OPENAI_EMBEDDING_V1',
    'openai',
    'text-embedding-3-large',
    3072,
    1,
    true
);

CREATE TABLE rag_chunk_embedding (
    chunk_id uuid NOT NULL REFERENCES rag_chunk(id) ON DELETE CASCADE,
    embedding_profile_id uuid NOT NULL REFERENCES rag_embedding_profile(id) ON DELETE RESTRICT,
    embedding vector(3072) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (chunk_id, embedding_profile_id)
);

CREATE TABLE rag_code_symbol (
    id uuid PRIMARY KEY,
    source_version_id uuid NOT NULL REFERENCES rag_source_version(id) ON DELETE RESTRICT,
    chunk_id uuid REFERENCES rag_chunk(id) ON DELETE SET NULL,
    language varchar(32) NOT NULL,
    package_name varchar(512),
    qualified_name varchar(1024) NOT NULL,
    signature text,
    path text NOT NULL,
    start_line integer NOT NULL CHECK (start_line > 0),
    end_line integer NOT NULL CHECK (end_line >= start_line),
    active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (source_version_id, qualified_name, path, start_line)
);
CREATE INDEX rag_code_symbol_name_trgm_idx ON rag_code_symbol USING gin (qualified_name gin_trgm_ops);
CREATE INDEX rag_code_symbol_source_idx ON rag_code_symbol (source_version_id, active);

CREATE TABLE rag_code_relation (
    id uuid PRIMARY KEY,
    source_version_id uuid NOT NULL REFERENCES rag_source_version(id) ON DELETE RESTRICT,
    from_symbol_id uuid NOT NULL REFERENCES rag_code_symbol(id) ON DELETE CASCADE,
    to_symbol_id uuid REFERENCES rag_code_symbol(id) ON DELETE SET NULL,
    to_qualified_name varchar(1024) NOT NULL,
    relation_type varchar(32) NOT NULL CHECK (relation_type IN ('IMPORT', 'INHERITANCE', 'DECLARATION', 'REFERENCE')),
    confidence numeric(4,3) NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX rag_code_relation_from_idx ON rag_code_relation (from_symbol_id, relation_type);
CREATE INDEX rag_code_relation_source_idx ON rag_code_relation (source_version_id, active);

CREATE TABLE rag_deletion_ledger (
    id uuid PRIMARY KEY,
    source_id uuid NOT NULL REFERENCES rag_source(id) ON DELETE RESTRICT,
    source_version_id uuid NOT NULL REFERENCES rag_source_version(id) ON DELETE RESTRICT,
    job_id uuid NOT NULL REFERENCES rag_ingestion_job(id) ON DELETE RESTRICT,
    state varchar(32) NOT NULL CHECK (state IN ('PENDING', 'SUCCEEDED', 'FAILED')),
    excluded_at timestamptz NOT NULL,
    policy_deadline_at timestamptz NOT NULL,
    chunks_deleted integer NOT NULL DEFAULT 0 CHECK (chunks_deleted >= 0),
    embeddings_deleted integer NOT NULL DEFAULT 0 CHECK (embeddings_deleted >= 0),
    symbols_deleted integer NOT NULL DEFAULT 0 CHECK (symbols_deleted >= 0),
    relations_deleted integer NOT NULL DEFAULT 0 CHECK (relations_deleted >= 0),
    error_code varchar(64),
    completed_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE rag_evaluation_case (
    id uuid PRIMARY KEY,
    case_key varchar(128) NOT NULL UNIQUE,
    question text NOT NULL,
    locale varchar(16) NOT NULL CHECK (locale IN ('ko-KR', 'en-US')),
    expected_state varchar(32) NOT NULL CHECK (expected_state IN ('ANSWERED', 'ABSTAINED')),
    expected_citation_ids uuid[] NOT NULL DEFAULT '{}',
    forbidden_claims text[] NOT NULL DEFAULT '{}',
    classification varchar(8) NOT NULL DEFAULT 'D0' CHECK (classification = 'D0'),
    active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE rag_evaluation_run (
    id uuid PRIMARY KEY,
    name varchar(128) NOT NULL,
    source_profile_ids varchar(64)[],
    compatibility_set_id uuid REFERENCES rag_compatibility_set(id) ON DELETE RESTRICT,
    provider_profile_id varchar(64) NOT NULL,
    requested_by varchar(128) NOT NULL,
    state varchar(32) NOT NULL CHECK (state IN ('PENDING', 'RUNNING', 'SUCCEEDED', 'FAILED')),
    total_cases integer NOT NULL DEFAULT 0 CHECK (total_cases >= 0),
    passed_cases integer NOT NULL DEFAULT 0 CHECK (passed_cases >= 0 AND passed_cases <= total_cases),
    idempotency_key varchar(128) NOT NULL UNIQUE,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CHECK ((source_profile_ids IS NOT NULL) <> (compatibility_set_id IS NOT NULL))
);

CREATE TABLE rag_evaluation_result (
    id uuid PRIMARY KEY,
    evaluation_run_id uuid NOT NULL REFERENCES rag_evaluation_run(id) ON DELETE CASCADE,
    evaluation_case_id uuid NOT NULL REFERENCES rag_evaluation_case(id) ON DELETE RESTRICT,
    state varchar(32) NOT NULL CHECK (state IN ('ANSWERED', 'ABSTAINED', 'FAILED')),
    passed boolean NOT NULL,
    citation_ids uuid[] NOT NULL DEFAULT '{}',
    latency_ms integer CHECK (latency_ms IS NULL OR latency_ms >= 0),
    error_code varchar(64),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (evaluation_run_id, evaluation_case_id)
);

CREATE TABLE rag_provider_call (
    id uuid PRIMARY KEY,
    query_id uuid,
    evaluation_run_id uuid REFERENCES rag_evaluation_run(id) ON DELETE SET NULL,
    provider varchar(32) NOT NULL CHECK (provider IN ('openai', 'mock')),
    surface varchar(32) NOT NULL CHECK (surface IN ('responses-api', 'embeddings-api', 'batch-api')),
    provider_profile_id varchar(64) NOT NULL,
    profile_version integer NOT NULL CHECK (profile_version > 0),
    requested_model_id varchar(128) NOT NULL,
    returned_model_id varchar(128),
    reasoning_effort varchar(16),
    embedding_dimension integer CHECK (embedding_dimension IS NULL OR embedding_dimension BETWEEN 1 AND 4096),
    provider_request_id varchar(255),
    provider_response_id varchar(255),
    input_tokens integer CHECK (input_tokens IS NULL OR input_tokens >= 0),
    output_tokens integer CHECK (output_tokens IS NULL OR output_tokens >= 0),
    latency_ms integer NOT NULL CHECK (latency_ms >= 0),
    status varchar(32) NOT NULL CHECK (status IN ('SUCCEEDED', 'FAILED', 'REJECTED')),
    failure_class varchar(32) CHECK (failure_class IS NULL OR failure_class IN ('RETRYABLE', 'TERMINAL', 'MANUAL_REVIEW')),
    error_code varchar(64),
    correlation_id varchar(128) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (query_id IS NOT NULL OR evaluation_run_id IS NOT NULL)
);
CREATE INDEX rag_provider_call_query_idx ON rag_provider_call (query_id, created_at DESC);
CREATE INDEX rag_provider_call_evaluation_idx ON rag_provider_call (evaluation_run_id, created_at DESC);

REVOKE ALL ON ALL TABLES IN SCHEMA public FROM PUBLIC;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO techflow_rag_migrator;

GRANT SELECT, INSERT, UPDATE ON
    rag_source, rag_source_version, rag_compatibility_set, rag_compatibility_set_source,
    rag_ingestion_job, rag_deletion_ledger, rag_evaluation_case, rag_evaluation_run,
    rag_evaluation_result, rag_provider_call, rag_embedding_profile
TO techflow_rag_app;
GRANT SELECT ON rag_chunk, rag_chunk_embedding, rag_code_symbol, rag_code_relation TO techflow_rag_app;

GRANT SELECT ON rag_source, rag_source_version, rag_ingestion_job, rag_embedding_profile TO techflow_rag_source_fetcher;
GRANT INSERT, UPDATE ON rag_ingestion_job, rag_chunk, rag_chunk_embedding, rag_code_symbol, rag_code_relation TO techflow_rag_source_fetcher;

ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM PUBLIC;
