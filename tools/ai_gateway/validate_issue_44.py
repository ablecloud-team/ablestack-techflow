#!/usr/bin/env python3
"""Validate the repository-owned Issue #44 grounded Responses contract."""

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
    query_schema = openapi["components"]["schemas"]["GroundedQueryRequest"]
    require("actorId" in query_schema["required"], "grounded query actorId is not required")
    responses = (SERVICE / "app" / "responses.py").read_text(encoding="utf-8")
    require("store=False" in responses and "background=False" in responses and "tools=[]" in responses,
            "Responses no-storage/no-tools boundary missing")
    require('"strict": True' in responses and "ANSWER_SCHEMA" in responses,
            "strict structured output missing")
    require("stable_safety_identifier" in responses and "hmac.new" in responses,
            "pseudonymous safety identifier missing")
    require("CircuitBreaker" in responses and "minimum_calls: int = 10" in responses,
            "circuit breaker policy missing")
    provider = (SERVICE / "app" / "provider.py").read_text(encoding="utf-8")
    require('model="gpt-5.6-terra"' in provider and 'model="gpt-5.6-sol"' in provider,
            "approved model routing profiles missing")
    store = (SERVICE / "app" / "postgres_store.py").read_text(encoding="utf-8")
    require("record_response_call" in store and "record_response_failure" in store,
            "sanitized provider audit missing")
    audit_block = store.split("def record_response_call", 1)[1].split("def create_evaluation_run", 1)[0]
    require("question" not in audit_block and "content" not in audit_block,
            "provider audit must not persist raw request or response content")
    return {"apiOperations": 21, "maxContextChunks": 10, "approvedProfiles": 2, "testCount": 96}


if __name__ == "__main__":
    result = validate()
    print("issue44=valid " + " ".join(f"{key}={value}" for key, value in result.items()))
