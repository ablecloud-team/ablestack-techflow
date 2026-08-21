CREATE TABLE IF NOT EXISTS chat_reviewer_identity (
    user_id varchar(64) PRIMARY KEY,
    username varchar(128) NOT NULL,
    enabled boolean NOT NULL DEFAULT true,
    last_seen_at timestamptz NOT NULL DEFAULT now(),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS chat_reviewer_identity_username_idx
    ON chat_reviewer_identity (lower(username));

GRANT SELECT, INSERT, UPDATE, DELETE ON chat_reviewer_identity TO techflow_rag_app;
