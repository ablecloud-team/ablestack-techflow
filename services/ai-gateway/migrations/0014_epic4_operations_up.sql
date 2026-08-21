CREATE TABLE IF NOT EXISTS chat_assist_conversation (
    user_id varchar(128) PRIMARY KEY,
    username varchar(128) NOT NULL,
    state varchar(16) NOT NULL CHECK (state IN ('ACTIVE','RESOLVED')),
    context_version integer NOT NULL DEFAULT 1 CHECK (context_version > 0),
    opened_at timestamptz NOT NULL DEFAULT now(),
    resolved_at timestamptz,
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chat_assist_turn (
    id uuid PRIMARY KEY,
    user_id varchar(128) NOT NULL REFERENCES chat_assist_conversation(user_id) ON DELETE CASCADE,
    context_version integer NOT NULL CHECK (context_version > 0),
    post_id varchar(128) NOT NULL,
    role varchar(16) NOT NULL CHECK (role IN ('USER','ASSISTANT')),
    content text NOT NULL CHECK (length(content) BETWEEN 1 AND 16000),
    content_sha256 char(64) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (user_id, context_version, post_id, role)
);
CREATE INDEX IF NOT EXISTS chat_assist_turn_context_idx
    ON chat_assist_turn(user_id, context_version, created_at);

CREATE TABLE IF NOT EXISTS operation_failure (
    id uuid PRIMARY KEY,
    subsystem varchar(32) NOT NULL,
    operation varchar(64) NOT NULL,
    fingerprint char(64) NOT NULL UNIQUE,
    state varchar(16) NOT NULL CHECK (state IN ('OPEN','RETRYING','RECOVERED','DEAD_LETTER')),
    attempt_count integer NOT NULL DEFAULT 1 CHECK (attempt_count > 0),
    max_attempts integer NOT NULL DEFAULT 3 CHECK (max_attempts BETWEEN 1 AND 10),
    last_error_type varchar(128) NOT NULL,
    correlation_id varchar(128) NOT NULL,
    next_retry_at timestamptz,
    failure_notified_at timestamptz,
    recovery_notified_at timestamptz,
    first_failed_at timestamptz NOT NULL DEFAULT now(),
    last_failed_at timestamptz NOT NULL DEFAULT now(),
    recovered_at timestamptz,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS operation_failure_state_idx
    ON operation_failure(state, next_retry_at);

GRANT SELECT, INSERT, UPDATE, DELETE ON
    chat_assist_conversation, chat_assist_turn, operation_failure TO techflow_rag_app;
