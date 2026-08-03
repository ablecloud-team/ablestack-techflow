from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from tools.rag.validate_rag_poc_contract import validate_contract

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = json.loads((ROOT / "docs/decisions/techflow-rag-poc-contract.json").read_text(encoding="utf-8"))


class RagPocContractTests(unittest.TestCase):
    def assert_invalid(self, mutate) -> None:
        candidate = copy.deepcopy(CONTRACT)
        mutate(candidate)
        self.assertTrue(validate_contract(candidate))

    def test_repository_contract_is_valid(self):
        self.assertEqual([], validate_contract(CONTRACT))

    def test_missing_required_source_profile_is_rejected(self):
        self.assert_invalid(lambda data: data["sourceSnapshots"].pop())

    def test_missing_cloud_main_branch_is_rejected(self):
        self.assert_invalid(
            lambda data: data["sourceSnapshots"].__setitem__(
                slice(None),
                [item for item in data["sourceSnapshots"] if item["sourceId"] != "ablestack-cloud-main"],
            )
        )

    def test_cross_branch_source_fusion_is_rejected(self):
        self.assert_invalid(lambda data: data["sourcePolicy"].update(crossBranchFusionAllowed=True))

    def test_code_query_without_source_profile_is_rejected(self):
        self.assert_invalid(lambda data: data["sourcePolicy"].update(sourceProfileRequiredForCodeQuery=False))

    def test_cross_repository_query_without_compatibility_set_is_rejected(self):
        self.assert_invalid(lambda data: data["sourcePolicy"].update(compatibilitySetRequiredForCrossRepositoryQuery=False))

    def test_unapproved_cross_repository_fusion_is_rejected(self):
        self.assert_invalid(lambda data: data["retrieval"].update(unapprovedCrossRepositoryFusionAllowed=True))

    def test_code_execution_is_rejected(self):
        self.assert_invalid(lambda data: data["sourcePolicy"].update(buildOrCodeExecutionAllowed=True))

    def test_test_only_answer_is_rejected(self):
        self.assert_invalid(lambda data: data["answer"].update(testOnlyEvidenceMustAbstain=False))

    def test_generated_path_exclusion_is_required(self):
        self.assert_invalid(lambda data: data["sourcePolicy"].update(excludedPathSegments=["target"]))

    def test_symbol_aware_chunking_is_required(self):
        self.assert_invalid(lambda data: data["chunkingProfiles"]["SOURCE_CODE"].update(strategy="line-window"))

    def test_d1_collection_is_rejected(self):
        self.assert_invalid(lambda data: data["dataGate"]["D1"].update(collectionDefault=True))

    def test_raw_prompt_persistence_is_rejected(self):
        self.assert_invalid(lambda data: data["dataGate"].update(rawPromptPersistence=True))

    def test_ai_tool_execution_is_rejected(self):
        self.assert_invalid(lambda data: data["answer"].update(toolsEnabled=True))

    def test_answer_without_citation_contract_is_rejected(self):
        self.assert_invalid(lambda data: data["answer"].update(citationRequiredForAnswered=False))

    def test_filter_after_retrieval_is_rejected(self):
        self.assert_invalid(lambda data: data["retrieval"].update(branchCommitFilterBeforeRetrieval=False))

    def test_hnsw_default_is_rejected(self):
        self.assert_invalid(lambda data: data["retrieval"]["hnsw"].update(enabled=True))

    def test_deletion_slo_over_seven_days_is_rejected(self):
        self.assert_invalid(lambda data: data["deletion"].update(maximumCompletionDays=8))

    def test_missing_code_deletion_store_is_rejected(self):
        self.assert_invalid(lambda data: data["deletion"].update(derivedStores=["chunks", "embeddings"]))

    def test_low_code_citation_rate_is_rejected(self):
        self.assert_invalid(lambda data: data["qualityGates"].update(codeCitationResolvableRate=0.99))

    def test_unknown_dependency_is_rejected(self):
        self.assert_invalid(lambda data: data["workItems"][5].update(dependsOn=[99]))

    def test_non_idempotent_mutation_is_rejected(self):
        def mutate(data):
            endpoint = next(item for item in data["api"] if item["path"] == "/v1/sources")
            endpoint["idempotencyRequired"] = False

        self.assert_invalid(mutate)


if __name__ == "__main__":
    unittest.main()
