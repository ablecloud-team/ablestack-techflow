#!/usr/bin/env python3
"""Validate the repository-owned Issue #43 implementation contract."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SERVICE = ROOT / "services" / "ai-gateway"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def validate() -> dict[str, int]:
    openapi = json.loads((SERVICE / "openapi" / "techflow-ai-gateway-v1.json").read_text(encoding="utf-8"))
    operations = [operation for path in openapi["paths"].values() for method, operation in path.items()
                  if method.lower() in {"get", "post", "put", "patch", "delete"}]
    require(len(operations) == 21, "OpenAPI operation count must be 21")
    require("/v1/jobs/{jobId}/run" in openapi["paths"], "job execution endpoint missing")
    require("/v1/rag/retrieve" in openapi["paths"], "retrieval endpoint missing")
    migration = (SERVICE / "migrations" / "0005_parser_embedding_retrieval_up.sql").read_text(encoding="utf-8")
    require("num_nonnulls(query_id, evaluation_run_id, ingestion_job_id) = 1" in migration,
            "provider audit subject constraint missing")
    chunking = (SERVICE / "app" / "chunking.py").read_text(encoding="utf-8")
    require("FALLBACK_MAX_LINES = 160" in chunking and "FALLBACK_OVERLAP_LINES = 20" in chunking,
            "fallback profile mismatch")
    indexing = (SERVICE / "app" / "indexing.py").read_text(encoding="utf-8")
    require("k: int = 60" in indexing and '0.6 if source_kinds.get(chunk_id) == "TEST_CODE"' in indexing,
            "RRF policy mismatch")
    embedding = (SERVICE / "app" / "embedding.py").read_text(encoding="utf-8")
    require("dimensions=self.profile.embedding_dimension" in embedding, "embedding dimension binding missing")
    require("api_key_file" in embedding and "OPENAI_API_KEY" not in embedding,
            "runtime secret file boundary mismatch")
    manifest = json.loads((SERVICE / "migrations" / "manifest.json").read_text(encoding="utf-8"))
    require(manifest["issue"] == 43 and len(manifest["files"]) == 12, "migration manifest mismatch")
    return {"apiOperations": len(operations), "migrationFiles": len(manifest["files"]),
            "embeddingDimension": 3072, "fallbackLines": 160, "rrfK": 60}


if __name__ == "__main__":
    result = validate()
    print("issue43=valid " + " ".join(f"{key}={value}" for key, value in result.items()))
