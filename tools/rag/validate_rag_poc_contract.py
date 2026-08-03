#!/usr/bin/env python3
"""Validate the machine-readable TechFlow documentation and source-code RAG contract."""

from __future__ import annotations

import json
import sys
from pathlib import Path

EXPECTED_STATES = {"ANSWERED", "ABSTAINED", "FAILED"}
EXPECTED_FAILURE_CLASSES = {"RETRYABLE", "TERMINAL", "MANUAL_REVIEW"}
EXPECTED_WORK_ITEMS = set(range(41, 47))
EXPECTED_SOURCE_IDS = {
    "ablestack-docs-public",
    "ablestack-cloud-main",
    "ablestack-cloud-diplo",
    "ablestack-cloud-europa",
    "ablestack-wall-main",
    "ablestack-cockpit-plugin-diplo",
    "ablestack-genie-master",
    "ablestack-kickstart-master",
    "ablestack-qemu-exec-tools-main",
}
EXPECTED_SOURCE_PROFILES = {
    "SHARED_DOCS",
    "CLOUD_MAIN",
    "CLOUD_DIPLO",
    "CLOUD_EUROPA",
    "WALL_MAIN",
    "COCKPIT_DIPLO",
    "GENIE_MASTER",
    "KICKSTART_MASTER",
    "QEMU_EXEC_TOOLS_MAIN",
}
EXPECTED_REPOSITORIES = {
    "ablecloud-team/ablestack-docs",
    "ablecloud-team/ablestack-cloud",
    "ablecloud-team/ablestack-wall",
    "ablecloud-team/ablestack-cockpit-plugin",
    "ablecloud-team/ablestack-genie",
    "ablecloud-team/ablestack-kickstart",
    "ablecloud-team/ablestack-qemu-exec-tools",
}
EXPECTED_SOURCE_KINDS = {"DOCUMENTATION", "SOURCE_CODE", "TEST_CODE", "BUILD_SCHEMA"}
EXPECTED_DERIVED_STORES = {"chunks", "embeddings", "symbols", "relations", "caches", "evaluation-links"}
EXPECTED_CHUNK_PROFILES = {"DOCUMENTATION", "SOURCE_CODE", "TEST_CODE", "BUILD_SCHEMA"}
MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def load_contract(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_contract(data: dict) -> list[str]:
    errors: list[str] = []
    if data.get("schemaVersion") != "1.2":
        errors.append("schemaVersion must be 1.2")
    if data.get("issue") != 20 or data.get("parentEpic") != 4:
        errors.append("issue and parentEpic must be 20 and 4")

    sources = data.get("sourceSnapshots", [])
    if {item.get("sourceId") for item in sources} != EXPECTED_SOURCE_IDS:
        errors.append("source snapshots must include all approved ABLESTACK repositories and Cloud branches")
    if {item.get("sourceProfile") for item in sources} != EXPECTED_SOURCE_PROFILES:
        errors.append("source profiles are incomplete")
    if {item.get("repository") for item in sources} != EXPECTED_REPOSITORIES:
        errors.append("source repositories are incomplete")
    for source in sources:
        if source.get("classification") != "D0":
            errors.append(f"source must be D0: {source.get('sourceId')}")
        if len(source.get("commit", "")) != 40:
            errors.append(f"source commit must be 40 characters: {source.get('sourceId')}")
        if source.get("eligibleFiles", 0) <= 0:
            errors.append(f"source eligible file count missing: {source.get('sourceId')}")
    cloud_sources = [item for item in sources if item.get("repository") == "ablecloud-team/ablestack-cloud"]
    if {item.get("branch") for item in cloud_sources} != {"main", "ablestack-diplo", "ablestack-europa"}:
        errors.append("ablestack-cloud must include main Diplo and Europa branches")
    if any(item.get("license") != "Apache-2.0" for item in cloud_sources):
        errors.append("ablestack-cloud source license must be Apache-2.0")

    source_policy = data.get("sourcePolicy", {})
    if source_policy.get("branchHeadTracking") != "LATEST_CANDIDATE_PINNED_ON_APPROVAL":
        errors.append("latest branch heads must be candidates pinned on approval")
    if not source_policy.get("branchIsolationRequired") or not source_policy.get("sourceProfileRequiredForCodeQuery"):
        errors.append("branch isolation and code source profile are required")
    if not source_policy.get("compatibilitySetRequiredForCrossRepositoryQuery"):
        errors.append("cross repository queries require a compatibility set")
    if source_policy.get("crossBranchFusionAllowed") is not False:
        errors.append("cross branch fusion must be disabled")
    if source_policy.get("unapprovedCrossRepositoryFusionAllowed") is not False:
        errors.append("unapproved cross repository fusion must be disabled")
    if set(source_policy.get("allowedSourceKinds", [])) != EXPECTED_SOURCE_KINDS:
        errors.append("allowed source kinds are incomplete")
    if source_policy.get("binaryFilesAllowed") is not False:
        errors.append("binary files must be denied")
    if source_policy.get("repositoryHooksAllowed") is not False or source_policy.get("buildOrCodeExecutionAllowed") is not False:
        errors.append("repository hooks build and code execution must be disabled")
    if source_policy.get("testCodeMayBeSoleCitation") is not False:
        errors.append("test code must not be the sole citation")
    if not source_policy.get("repositoryAccessAuthorizationRequired"):
        errors.append("repository access authorization is required")
    required_excludes = {"target", "build", "dist", "node_modules", "vendor", "third_party", "generated", "gen"}
    if not required_excludes.issubset(set(source_policy.get("excludedPathSegments", []))):
        errors.append("generated and vendor exclusions are incomplete")
    if source_policy.get("maximumTextFileBytes", 0) > 1048576:
        errors.append("source file maximum must not exceed 1 MiB")

    gate = data.get("dataGate", {})
    for level in ("D0", "D1", "D2", "D3"):
        if level not in gate:
            errors.append(f"dataGate missing {level}")
    if not gate.get("D0", {}).get("collectionDefault"):
        errors.append("D0 collection must be enabled")
    for level in ("D1", "D2", "D3"):
        rule = gate.get(level, {})
        if rule.get("collectionDefault") or rule.get("embeddingAllowed") or rule.get("providerAllowed"):
            errors.append(f"{level} must be disabled")
    for field in ("rawPromptPersistence", "rawResponsePersistence", "credentialPersistence"):
        if gate.get(field) is not False:
            errors.append(f"{field} must be false")

    forbidden_ai = set(data.get("responsibility", {}).get("forbiddenForAi", []))
    required_forbidden = {"shell-execution", "api-execution", "activepieces-flow-execution", "ablestack-resource-action", "source-code-execution"}
    if forbidden_ai != required_forbidden:
        errors.append("AI execution prohibitions are incomplete")
    if set(data.get("queryStates", [])) != EXPECTED_STATES:
        errors.append("query states are incomplete")
    if set(data.get("failureClasses", [])) != EXPECTED_FAILURE_CLASSES:
        errors.append("failure classes are incomplete")

    table_names = {item.get("name") for item in data.get("tables", [])}
    if not {"rag_compatibility_set", "rag_compatibility_set_source"}.issubset(table_names):
        errors.append("compatibility set tables are required")

    endpoints = data.get("api", [])
    seen: set[tuple[str, str]] = set()
    for endpoint in endpoints:
        key = (endpoint.get("method", ""), endpoint.get("path", ""))
        if key in seen:
            errors.append(f"duplicate endpoint {key}")
        seen.add(key)
        if endpoint.get("method") in MUTATING_METHODS and endpoint.get("path") != "/v1/rag/query":
            if not endpoint.get("idempotencyRequired"):
                errors.append(f"mutating endpoint requires idempotency: {key}")
    if ("POST", "/v1/compatibility-sets") not in seen:
        errors.append("compatibility set endpoint is required")

    quarantine = data.get("quarantine", {})
    if not quarantine.get("requiresHumanApproval") or quarantine.get("partialActivationAllowed") is not False:
        errors.append("quarantine must require approval and deny partial activation")
    if not {"branch-allowlist", "commit-pin", "secret-patterns", "generated-vendor-path", "binary-file"}.issubset(set(quarantine.get("checks", []))):
        errors.append("code quarantine checks are incomplete")

    profiles = data.get("chunkingProfiles", {})
    if not EXPECTED_CHUNK_PROFILES.issubset(set(profiles)):
        errors.append("chunking profiles are incomplete")
    if profiles.get("SOURCE_CODE", {}).get("strategy") != "symbol-aware-tree-sitter":
        errors.append("source code chunking must be symbol aware")
    if not profiles.get("SOURCE_CODE", {}).get("fallback"):
        errors.append("source code chunking requires deterministic fallback")

    retrieval = data.get("retrieval", {})
    if retrieval.get("mode") != "hybrid-exact-identifier":
        errors.append("retrieval must combine exact vector FTS and identifier")
    for field in ("authorizationFilterBeforeRetrieval", "sourceProfileFilterBeforeRetrieval", "compatibilitySetFilterBeforeRetrieval", "branchCommitFilterBeforeRetrieval"):
        if not retrieval.get(field):
            errors.append(f"retrieval filter required: {field}")
    if retrieval.get("crossBranchFusionAllowed") is not False:
        errors.append("retrieval cross branch fusion must be disabled")
    if retrieval.get("unapprovedCrossRepositoryFusionAllowed") is not False:
        errors.append("retrieval unapproved cross repository fusion must be disabled")
    if retrieval.get("finalTopK", 0) > 10:
        errors.append("finalTopK must not exceed 10")
    hnsw = retrieval.get("hnsw", {})
    if hnsw.get("enabled") is not False or not hnsw.get("requiresBenchmark"):
        errors.append("HNSW must be disabled and benchmark gated")

    answer = data.get("answer", {})
    if not answer.get("citationRequiredForAnswered") or answer.get("toolsEnabled") is not False:
        errors.append("citation is required and AI tools must be disabled")
    if answer.get("documentsAndCodeAreInstructions") is not False:
        errors.append("documents and code must not be treated as instructions")
    if not answer.get("answerMustNameSourceProfiles") or not answer.get("answerMustNameCompatibilitySetWhenUsed") or not answer.get("branchConflictMustAbstain") or not answer.get("testOnlyEvidenceMustAbstain"):
        errors.append("branch aware answer and abstention rules are incomplete")
    required_citation = {"sourceId", "sourceVersion", "repository", "branch", "commit", "path", "startLine", "endLine", "symbol", "chunkId"}
    if set(answer.get("citationFields", [])) != required_citation:
        errors.append("code citation fields are incomplete")

    provider = data.get("provider", {})
    if provider.get("credentialStorage") != "protected-runtime-injection" or not provider.get("retentionAndTrainingMustBeDisabled"):
        errors.append("provider credential retention and training policy invalid")
    if provider.get("retry", {}).get("maximumAttempts", 0) > 3:
        errors.append("provider retry maximum must not exceed 3")

    deletion = data.get("deletion", {})
    if not deletion.get("immediateSearchExclusion"):
        errors.append("withdrawn source must be excluded immediately")
    if set(deletion.get("derivedStores", [])) != EXPECTED_DERIVED_STORES:
        errors.append("deletion stores are incomplete")
    if deletion.get("maximumCompletionDays", 999) > 7 or deletion.get("testCompletionMinutes", 999) > 15:
        errors.append("deletion limits exceeded")
    if not deletion.get("reapplyLedgerAfterRestore"):
        errors.append("deletion ledger must be reapplied after restore")

    quality = data.get("qualityGates", {})
    if quality.get("minimumGoldenQuestions", 0) < 50 or quality.get("minimumCodeQuestions", 0) < 20:
        errors.append("at least 50 golden questions including 20 code questions are required")
    if quality.get("answeredCitationRate") != 1.0 or quality.get("codeCitationResolvableRate") != 1.0:
        errors.append("answer and code citations must be fully resolvable")
    if (
        quality.get("maximumCrossBranchEvidenceRate") != 0.0
        or quality.get("maximumUnapprovedCrossRepositoryEvidenceRate") != 0.0
        or quality.get("maximumTestOnlyAnsweredRate") != 0.0
    ):
        errors.append("cross branch unapproved cross repository and test-only answers must be zero")
    for field in ("maximumRestrictedIndexedDocuments", "maximumDerivedRowsAfterDeletion", "maximumPersistedRawPrompts", "maximumPersistedRawResponses"):
        if quality.get(field) != 0:
            errors.append(f"{field} must be zero")

    work_items = data.get("workItems", [])
    issue_ids = {item.get("issue") for item in work_items}
    if issue_ids != EXPECTED_WORK_ITEMS:
        errors.append("workItems must be issues 41 through 46")
    for item in work_items:
        for dependency in item.get("dependsOn", []):
            if dependency not in issue_ids or dependency >= item.get("issue"):
                errors.append(f"invalid dependency for issue {item.get('issue')}: {dependency}")
    return errors


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("docs/decisions/techflow-rag-poc-contract.json")
    data = load_contract(path)
    errors = validate_contract(data)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    sources = data["sourceSnapshots"]
    print(
        "contract=valid "
        f"api={len(data['api'])} tables={len(data['tables'])} workItems={len(data['workItems'])} "
        f"sources={len(sources)} eligibleFiles={sum(item['eligibleFiles'] for item in sources)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
