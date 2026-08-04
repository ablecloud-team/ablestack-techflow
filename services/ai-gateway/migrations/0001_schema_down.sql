-- Destructive rollback. Disable flows, stop the gateway, back up, and require --allow-destructive-rollback.
DROP TABLE IF EXISTS rag_provider_call;
DROP TABLE IF EXISTS rag_evaluation_result;
DROP TABLE IF EXISTS rag_evaluation_run;
DROP TABLE IF EXISTS rag_evaluation_case;
DROP TABLE IF EXISTS rag_deletion_ledger;
DROP TABLE IF EXISTS rag_code_relation;
DROP TABLE IF EXISTS rag_code_symbol;
DROP TABLE IF EXISTS rag_chunk_embedding;
DROP TABLE IF EXISTS rag_embedding_profile;
DROP TABLE IF EXISTS rag_chunk;
DROP TABLE IF EXISTS rag_ingestion_job;
DROP TABLE IF EXISTS rag_compatibility_set_source;
DROP TABLE IF EXISTS rag_compatibility_set;
DROP TABLE IF EXISTS rag_source_version;
DROP TABLE IF EXISTS rag_source;
