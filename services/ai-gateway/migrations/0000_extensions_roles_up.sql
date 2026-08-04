-- Issue #41 privileged bootstrap. Run as the techflow_rag database owner.
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'techflow_rag_migrator') THEN
        CREATE ROLE techflow_rag_migrator NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'techflow_rag_app') THEN
        CREATE ROLE techflow_rag_app NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'techflow_rag_source_fetcher') THEN
        CREATE ROLE techflow_rag_source_fetcher NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
    END IF;
END
$$;

REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO techflow_rag_migrator, techflow_rag_app, techflow_rag_source_fetcher;
GRANT CREATE ON SCHEMA public TO techflow_rag_migrator;
