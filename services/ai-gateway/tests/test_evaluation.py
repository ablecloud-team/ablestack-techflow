import copy
import json
from pathlib import Path
import unittest

from app.evaluation import GoldenSetError, judge_case, load_golden_set, summarize_results, validate_golden_set


class EvaluationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.golden = load_golden_set()

    def test_golden_set_has_required_coverage(self) -> None:
        self.assertGreaterEqual(self.golden["caseCount"], 50)
        self.assertEqual(self.golden["caseCount"], len(self.golden["cases"]))
        self.assertGreaterEqual(sum(case["category"] in {"PRODUCTION_CODE", "API_SCHEMA", "BUILD_SCHEMA", "PRODUCTION_POLICY"} for case in self.golden["cases"]), 20)

    def test_golden_set_has_all_security_boundary_cases(self) -> None:
        tags = {tag for item in self.golden["cases"] for tag in item.get("tags", [])}
        self.assertTrue({"test-only", "prompt-injection", "secret", "allowlist"}.issubset(tags))

    def test_duplicate_case_key_is_rejected(self) -> None:
        value = copy.deepcopy(self.golden)
        value["cases"][1]["caseKey"] = value["cases"][0]["caseKey"]
        with self.assertRaises(GoldenSetError):
            validate_golden_set(value)

    def test_non_d0_case_is_rejected(self) -> None:
        value = copy.deepcopy(self.golden)
        value["cases"][0]["classification"] = "D1"
        with self.assertRaises(GoldenSetError):
            validate_golden_set(value)

    def test_answered_case_requires_matching_resolvable_citation(self) -> None:
        case = next(item for item in self.golden["cases"] if item["caseKey"] == "GENIE-001")
        rule = case["expectedCitations"][0]
        result = {"state": "ANSWERED", "answer": "인프라 배포 자동화 플랫폼", "citations": [{**rule, "startLine": 1, "endLine": 2}]}
        self.assertTrue(judge_case(case, result).passed)
        result["citations"][0]["branch"] = "wrong"
        self.assertFalse(judge_case(case, result).passed)

    def test_abstention_rejects_answer_or_citation(self) -> None:
        case = next(item for item in self.golden["cases"] if item["caseKey"] == "PROMPT-INJECTION-001")
        self.assertTrue(judge_case(case, {"state": "ABSTAINED", "answer": None, "citations": []}).passed)
        self.assertFalse(judge_case(case, {"state": "ABSTAINED", "answer": "추측", "citations": []}).passed)

    def test_summary_exposes_quality_and_security_metrics(self) -> None:
        records = [{
            "expectedState": "ABSTAINED", "actualState": "ABSTAINED", "tags": ["branch-isolation"],
            "latencyMs": 10, "providerProfileId": None, "generationProviderCalled": False,
            "citations": [], "automatedJudgment": {"passed": True, "codeLineResolvable": True},
            "reviewJudgment": {"reviewer": "Codex", "verdict": "ACCEPTED"},
        }]
        summary = summarize_results(records)
        self.assertEqual(1, summary["totalCases"])
        self.assertEqual(1, summary["correctAbstentionRate"])
        self.assertEqual(0, summary["isolationAnsweredViolations"])
        self.assertEqual(1, summary["codexAcceptedCases"])
        self.assertEqual(1, summary["codexAcceptedRate"])
        self.assertEqual(1, summary["codexCorrectAbstentionRate"])

    def test_expected_branch_specific_answer_is_not_an_isolation_violation(self) -> None:
        record = {
            "expectedState": "ANSWERED",
            "actualState": "ANSWERED",
            "tags": ["branch-isolation"],
            "citations": [{"chunkId": "1"}],
            "providerProfileId": "OPENAI_RESPONSES_TERRA_V1",
            "generationProviderCalled": True,
            "latencyMs": 100,
            "automatedJudgment": {"passed": True, "codeLineResolvable": True},
        }
        self.assertEqual(0, summarize_results([record])["isolationAnsweredViolations"])


if __name__ == "__main__":
    unittest.main()
