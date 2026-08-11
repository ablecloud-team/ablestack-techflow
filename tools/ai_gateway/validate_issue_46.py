#!/usr/bin/env python3
"""Validate the committed Issue #46 Golden Set and runtime contracts."""

from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
SERVICE = ROOT / "services/ai-gateway"
sys.path.insert(0, str(SERVICE))

from app.chunking import MAX_QUALIFIED_NAME_CHARS  # noqa: E402
from app.embedding import MAX_INPUT_BYTES  # noqa: E402
from app.evaluation import CODE_CATEGORIES, REQUIRED_PROFILES, load_golden_set  # noqa: E402


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def validate() -> dict[str, int | bool]:
    golden = load_golden_set()
    cases = golden["cases"]
    openapi = json.loads((SERVICE / "openapi/techflow-ai-gateway-v1.json").read_text(encoding="utf-8"))
    operations = [
        operation
        for methods in openapi["paths"].values()
        for method, operation in methods.items()
        if method.lower() in {"get", "post", "delete", "put", "patch"}
    ]
    require(len(operations) == 23, "OpenAPI operation count must be 23")
    require("/v1/evaluations/runs/{runId}/execute" in openapi["paths"], "evaluation execution endpoint missing")
    require("/v1/evaluations/runs/{runId}/results" in openapi["paths"], "evaluation result endpoint missing")
    require(MAX_INPUT_BYTES == 7936, "embedding input safety boundary drifted")
    require(MAX_QUALIFIED_NAME_CHARS == 1024, "qualified-name schema boundary drifted")
    require(sum(item["category"] in CODE_CATEGORIES for item in cases) >= 20, "code/schema case floor missed")
    require(
        REQUIRED_PROFILES.issubset({profile for item in cases for profile in item["sourceProfileIds"]}),
        "approved source profile coverage missed",
    )
    require(sum(item["expectedState"] == "ABSTAINED" for item in cases) >= 5, "abstention case floor missed")
    return {
        "valid": True,
        "apiOperations": len(operations),
        "goldenCases": len(cases),
        "codeSchemaCases": sum(item["category"] in CODE_CATEGORIES for item in cases),
        "profiles": len(REQUIRED_PROFILES),
    }


if __name__ == "__main__":
    print(json.dumps(validate(), ensure_ascii=False, sort_keys=True))
