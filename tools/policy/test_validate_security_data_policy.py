from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from tools.policy.validate_security_data_policy import validate_document


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "docs" / "decisions" / "techflow-security-data-policy.json"


class SecurityDataPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = json.loads(SOURCE.read_text(encoding="utf-8"))

    def assert_invalid(self, policy: dict, text: str) -> None:
        self.assertTrue(any(text in error for error in validate_document(policy)))

    def test_repository_policy_is_valid(self) -> None:
        self.assertEqual([], validate_document(self.policy))

    def test_duplicate_threat_id_is_rejected(self) -> None:
        policy = copy.deepcopy(self.policy)
        policy["threats"][1]["id"] = policy["threats"][0]["id"]
        self.assert_invalid(policy, "duplicate ids")

    def test_unknown_control_is_rejected(self) -> None:
        policy = copy.deepcopy(self.policy)
        policy["threats"][0]["controls"].append("C99")
        self.assert_invalid(policy, "unknown controls")

    def test_high_residual_risk_is_rejected(self) -> None:
        policy = copy.deepcopy(self.policy)
        policy["threats"][0]["residualLikelihood"] = 3
        policy["threats"][0]["residualImpact"] = 4
        self.assert_invalid(policy, "residual risk exceeds")

    def test_invalid_classification_order_is_rejected(self) -> None:
        policy = copy.deepcopy(self.policy)
        policy["classifications"][1]["rank"] = 2
        self.assert_invalid(policy, "classifications must")

    def test_d3_default_collection_is_rejected(self) -> None:
        policy = copy.deepcopy(self.policy)
        policy["retentionPolicies"][0]["collectionDefault"] = True
        self.assert_invalid(policy, "D3 collectionDefault")

    def test_raw_webhook_retention_is_zero(self) -> None:
        policy = copy.deepcopy(self.policy)
        policy["retentionPolicies"][0]["retentionDays"] = 1
        self.assert_invalid(policy, "R01: retentionDays")

    def test_raw_ai_retention_is_bounded_and_opt_in(self) -> None:
        policy = copy.deepcopy(self.policy)
        item = next(item for item in policy["retentionPolicies"] if item["id"] == "R13")
        item["retentionDays"] = 31
        self.assert_invalid(policy, "raw AI data")

    def test_d2_cannot_be_enabled_for_rag_p1(self) -> None:
        policy = copy.deepcopy(self.policy)
        policy["ragP1Gate"]["defaultAllowedClassifications"].append("D2")
        self.assert_invalid(policy, "only D0")

    def test_deletion_slo_cannot_exceed_seven_days(self) -> None:
        policy = copy.deepcopy(self.policy)
        policy["deletionPolicy"]["primaryAndDerivedSloDays"] = 8
        self.assert_invalid(policy, "deletion SLO")

    def test_legal_hold_requires_two_approvers(self) -> None:
        policy = copy.deepcopy(self.policy)
        policy["legalHold"]["requiredApprovers"] = ["product-owner"]
        self.assert_invalid(policy, "product and security approvals")

    def test_legal_hold_review_is_bounded(self) -> None:
        policy = copy.deepcopy(self.policy)
        policy["legalHold"]["maximumReviewIntervalDays"] = 91
        self.assert_invalid(policy, "review interval")


if __name__ == "__main__":
    unittest.main()
