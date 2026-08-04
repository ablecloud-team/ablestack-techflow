-- Run only after 0001_schema_down.sql and after runtime login roles no longer inherit these groups.
REVOKE USAGE ON SCHEMA public FROM techflow_rag_source_fetcher, techflow_rag_app, techflow_rag_migrator;
DROP ROLE IF EXISTS techflow_rag_source_fetcher;
DROP ROLE IF EXISTS techflow_rag_app;
DROP ROLE IF EXISTS techflow_rag_migrator;
DROP EXTENSION IF EXISTS pg_trgm;
DROP EXTENSION IF EXISTS vector;
