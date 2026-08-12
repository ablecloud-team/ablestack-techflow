CREATE TABLE IF NOT EXISTS community_case (
    id uuid PRIMARY KEY,
    discussion_id varchar(32) NOT NULL UNIQUE,
    discussion_url text NOT NULL,
    title varchar(200) NOT NULL,
    state varchar(32) NOT NULL CHECK (state IN ('DRAFT_PENDING','APPROVED','REJECTED','PUBLISHED')),
    draft_version integer NOT NULL DEFAULT 1 CHECK (draft_version > 0),
    draft_answer text,
    answer_state varchar(32),
    citations jsonb NOT NULL DEFAULT '[]'::jsonb,
    approval_version integer NOT NULL DEFAULT 0 CHECK (approval_version >= 0),
    reviewer varchar(128),
    approved_at timestamptz,
    published_post_id varchar(32),
    published_post_url text,
    published_at timestamptz,
    correlation_id varchar(128) NOT NULL,
    idempotency_key varchar(128) NOT NULL UNIQUE,
    source_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS community_case_event (
    id uuid PRIMARY KEY,
    case_id uuid NOT NULL REFERENCES community_case(id) ON DELETE CASCADE,
    event_type varchar(32) NOT NULL,
    actor varchar(128) NOT NULL,
    idempotency_key varchar(128) UNIQUE,
    correlation_id varchar(128) NOT NULL,
    details jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS community_case_state_created_idx ON community_case(state, created_at DESC);
CREATE INDEX IF NOT EXISTS community_case_event_case_idx ON community_case_event(case_id, created_at);

GRANT SELECT, INSERT, UPDATE, DELETE ON community_case, community_case_event TO techflow_rag_app;
