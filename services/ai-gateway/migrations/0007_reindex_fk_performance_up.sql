-- Issue #46: keep atomic active-source reindex replacement bounded.
-- PostgreSQL does not automatically index the referencing side of a foreign key.
CREATE INDEX IF NOT EXISTS rag_code_symbol_chunk_idx
    ON rag_code_symbol (chunk_id)
    WHERE chunk_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS rag_code_relation_to_symbol_idx
    ON rag_code_relation (to_symbol_id)
    WHERE to_symbol_id IS NOT NULL;
