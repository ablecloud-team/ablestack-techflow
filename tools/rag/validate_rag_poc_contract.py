#!/usr/bin/env python3
"""Validate the machine-readable TechFlow RAG PoC design contract."""

from __future__ import annotations

import json
import sys
from pathlib import Path


EXPECTED_STATES = {"ANSWERED", "ABSTAINED", "FAILED"}
EXPECTED_FAILURE_CLASSES = {"RETRYABLE", "TERMINAL", "MANUAL_REVIEW"}
EXPECTED_WORK_ITEMS = set(range(41, 47))
EXPECTED_DERIVED_STORES = {"chunks", "embeddings", "caches", "evaluation-links"}
MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def load_contract(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_contract(data: dict) -> list[str]:
    errors: list[str] = []

    if data.get("schemaVersion") != "1.0":
        errors.append("schemaVersion must be 1.0")
    if data.get("issue") != 20 or data.get("parentEpic") != 4:
        errors.append("issue and parentEpic must be 20 and 4")

    source = data.get("sourceSnapshot", {})
    if source.get("repository") != "ablecloud-team/ablestack-docs":
        errors.append("P1 source repository must be ablecloud-team/ablestack-docs")
    if source.get("allowedPath") != "docs/**/*.md":
        errors.append("P1 allowed path must be docs/**/*.md")
    if source.get("classification") != "D0":
        errors.append("P1 source classification must be D0")
    if not source.get("commit") or len(source.get("commit", "")) != 40:
        errors.append("source snapshot must include a 40 character commit sha")

    gate = data.get("dataGate", {})
    for level in ("D0", "D1", "D2", "D3"):
        if level not in gate:
            errors.append(f"dataGate missing {level}")
    if not gate.get("D0", {}).get("collectionDefault"):
        errors.append("D0 collection must be enabled")
    for level in ("D1", "D2", "D3"):
        rule = gate.get(level, {})
        if rule.get("collectionDefault") or rule.get("embeddingAllowed") or rule.get("providerAllowed"):
            errors.append(f"{level} must be disabled for P1 collection embedding and provider")
    for field in ("rawPromptPersistence", "rawResponsePersistence", "credentialPersistence"):
        if gate.get(field) is not False:
            errors.append(f"{field} must be false")

    responsibility = data.get("responsibility", {})
    forbidden_ai = set(responsibility.get("forbiddenForAi", []))
    required_forbidden = {"shell-execution", "api-execution", "activepieces-flow-execution", "ablestack-resource-action"}
    if forbidden_ai != required_forbidden:
        errors.append("AI execution prohibitions are incomplete")

    if set(data.get("queryStates", [])) != EXPECTED_STATES:
        errors.append("queryStates must be ANSWERED ABSTAINED FAILED")
    if set(data.get("failureClasses", [])) != EXPECTED_FAILURE_CLASSES:
        errors.append("failureClasses are incomplete")

    endpoints = data.get("api", [])
    seen_endpoints: set[tuple[str, str]] = set()
    for endpoint in endpoints:
        key = (endpoint.get("method", ""), endpoint.get("path", ""))
        if key in seen_endpoints:
            errors.append(f"duplicate endpoint {key}")
        seen_endpoints.add(key)
        if endpoint.get("method") in MUTATING_METHODS and endpoint.get("path") != "/v1/rag/query":
            if not endpoint.get("idempotencyRequired"):
                errors.append(f"mutating endpoint requires idempotency: {key}")

    quarantine = data.get("quarantine", {})
    if not quarantine.get("requiresHumanApproval"):
        errors.append("quarantine requires human approval")
    if quarantine.get("partialActivationAllowed") is not False:
        errors.append("partial source activation must be disabled")

    retrieval = data.get("retrieval", {})
    if retrieval.get("mode") != "hybrid-exact":
        errors.append("P1 retrieval mode must be hybrid-exact")
    if not retrieval.get("authorizationFilterBeforeRetrieval"):
        errors.append("authorization filter must be applied before retrieval")
    if retrieval.get("finalTopK", 0) > 8:
        errors.append("finalTopK must not exceed 8")
    hnsw = retrieval.get("hnsw", {})
    if hnsw.get("enabled") is not False or not hnsw.get("requiresBenchmark"):
        errors.append("HNSW must be disabled and benchmark-gated in P1")

    answer = data.get("answer", {})
    if not answer.get("citationRequiredForAnswered"):
        errors.append("citation is required for ANSWERED")
    if answer.get("documentsAreInstructions") is not False:
        errors.append("retrieved documents must not be treated as instructions")
    if answer.get("toolsEnabled") is not False:
        errors.append("AI tools must be disabled")
    required_citation = {"sourceId", "sourceVersion", "uri", "title", "section", "chunkId"}
    if set(answer.get("citationFields", [])) != required_citation:
        errors.append("citation fields are incomplete")

    provider = data.get("provider", {})
    if provider.get("credentialStorage") != "protected-runtime-injection":
        errors.append("provider credentials must use protected runtime injection")
    if not provider.get("retentionAndTrainingMustBeDisabled"):
        errors.append("provider retention and training must be disabled")
    if provider.get("retry", {}).get("maximumAttempts", 0) > 3:
        errors.append("provider retry maximum must not exceed 3")

    deletion = data.get("deletion", {})
    if not deletion.get("immediateSearchExclusion"):
        errors.append("withdrawn source must be excluded from search immediately")
    if set(deletion.get("derivedStores", [])) != EXPECTED_DERIVED_STORES:
        errors.append("deletion derived stores are incomplete")
    if deletion.get("maximumCompletionDays", 999) > 7:
        errors.append("deletion SLO must not exceed 7 days")
    if deletion.get("testCompletionMinutes", 999) > 15:
        errors.append("P1 deletion test target must not exceed 15 minutes")
    if not deletion.get("reapplyLedgerAfterRestore"):
        errors.append("deletion ledger must be reapplied after restore")

    quality = data.get("qualityGates", {})
    if quality.get("minimumGoldenQuestions", 0) < 30:
        errors.append("at least 30 golden questions are required")
    if quality.get("answeredCitationRate") != 1.0:
        errors.append("ANSWERED citation rate must be 1.0")
    if quality.get("minimumAcceptableAnswerRate", 0) < 0.8:
        errors.append("acceptable answer rate must be at least 0.8")
    if quality.get("minimumCorrectAbstentionRate", 0) < 0.9:
        errors.append("correct abstention rate must be at least 0.9")
    for field in ("maximumRestrictedIndexedDocuments", "maximumDerivedRowsAfterDeletion", "maximumPersistedRawPrompts", "maximumPersistedRawResponses"):
        if quality.get(field) != 0:
            errors.append(f"{field} must be zero")

    work_items = data.get("workItems", [])
    issue_ids = {item.get("issue") for item in work_items}
    if issue_ids != EXPECTED_WORK_ITEMS:
        errors.append("workItems must be issues 41 through 46")
    for item in work_items:
        issue_id = item.get("issue")
        for dependency in item.get("dependsOn", []):
            if dependency not in issue_ids:
                errors.append(f"issue {issue_id} depends on unknown issue {dependency}")
            if dependency >= issue_id:
                errors.append(f"issue {issue_id} dependency must precede it: {dependency}")

    return errors


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("docs/decisions/techflow-rag-poc-contract.json")
    errors = validate_contract(load_contract(path))
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    data = load_contract(path)
    print(
        "contract=valid "
        f"api={len(data['api'])} tables={len(data['tables'])} "
        f"workItems={len(data['workItems'])} source={data['sourceSnapshot']['observedMarkdownFiles']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
