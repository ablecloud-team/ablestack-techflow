from __future__ import annotations

import json
from pathlib import Path
import unittest

from app.versioned_assist import (
    CURRENT_SOURCE_PROFILES,
    INTERNAL_REFERENCE_ONLY_PROFILE,
    PREVIEW_SOURCE_PROFILE,
    VERSIONED_SOURCE_PROFILES,
    coverage_payload,
    format_public_answer,
    projection_is_safe,
    versioned_plan,
)


class VersionedAssistPolicyTest(unittest.TestCase):
    def test_plan_reviews_docs_diplo_related_code_and_europa_preview(self) -> None:
        plan = versioned_plan("VM 배포가 실패합니다")
        self.assertEqual(list(VERSIONED_SOURCE_PROFILES), plan["sourceProfileIds"])
        self.assertIn("SHARED_DOCS", CURRENT_SOURCE_PROFILES)
        self.assertIn("CLOUD_DIPLO", CURRENT_SOURCE_PROFILES)
        self.assertEqual("CLOUD_EUROPA", PREVIEW_SOURCE_PROFILE)
        self.assertNotIn(INTERNAL_REFERENCE_ONLY_PROFILE, plan["sourceProfileIds"])

    def test_coverage_records_every_reviewed_profile(self) -> None:
        coverage = coverage_payload("VM 배포 오류", {
            "SHARED_DOCS": [{"chunkId": "1", "content": "VM 배포 절차", "path": "guide.md"}],
            "CLOUD_DIPLO": [],
        })
        self.assertEqual(len(VERSIONED_SOURCE_PROFILES), len(coverage))
        self.assertEqual("EVIDENCE_FOUND", coverage[0]["state"])
        self.assertEqual("NO_RELEVANT_EVIDENCE", coverage[1]["state"])

    def test_public_projection_removes_internal_lineage(self) -> None:
        citation = {
            "repository": "ablecloud-team/ablestack-cloud", "branch": "ablestack-diplo",
            "commit": "a" * 40, "path": "server/src/Foo.java", "startLine": 10, "endLine": 20,
            "sourceProfileId": "CLOUD_DIPLO",
        }
        result = {
            "state": "ANSWERED",
            "report": {
                "summary": "ablecloud-team/ablestack-cloud server/src/Foo.java:10에서 확인했습니다.",
                "observedFacts": ["CLOUD_DIPLO 현재 오류"],
                "diagnoses": [{"title": "현재 구현 결함"}],
                "recommendedActions": ["임시 조치를 적용합니다."],
                "unknowns": [],
                "currentAssessment": "CURRENT_DEFECT",
                "previewAssessment": "PREVIEW_IMPROVED",
                "previewGuidance": "github.com/ablecloud-team/ablestack-cloud 에서 개선을 확인했습니다.",
            },
            "citations": [citation],
        }
        answer = format_public_answer(result) or ""
        self.assertTrue(projection_is_safe(answer), answer)
        headings = ["### 증상", "### 원인", "### 해결 방법", "### 추가 고려사항", "### 적용 버전"]
        self.assertTrue(all(heading in answer for heading in headings), answer)
        self.assertEqual(sorted(answer.index(heading) for heading in headings), [answer.index(heading) for heading in headings])
        self.assertIn("ABLESTACK Cloud Diplo(현재 출시판)", answer)
        self.assertIn("ABLESTACK Cloud Europa(미출시 Preview)", answer)
        self.assertIn("개선이 진행 중", answer)
        self.assertNotIn("Foo.java", answer)
        self.assertNotIn("CLOUD_DIPLO", answer)

    def test_troubleshooting_sections_remain_when_optional_content_is_empty(self) -> None:
        answer = format_public_answer({
            "state": "ANSWERED",
            "report": {
                "summary": "현상을 확인했습니다.", "observedFacts": [], "diagnoses": [],
                "recommendedActions": [], "unknowns": [], "currentAssessment": "CURRENT_NORMAL",
                "previewAssessment": "NOT_APPLICABLE", "previewGuidance": None,
            },
            "citations": [],
        }) or ""
        self.assertIn("현재 근거에서 확정된 원인은 없습니다.", answer)
        self.assertIn("별도의 추가 고려사항은 확인되지 않았습니다.", answer)
        self.assertIn("차기 버전 비교는 적용 대상이 아닙니다.", answer)

    def test_versioned_golden_set_has_required_decision_cases(self) -> None:
        source = Path(__file__).parents[1] / "app" / "data" / "versioned-assist-golden-v1.json"
        payload = json.loads(source.read_text(encoding="utf-8"))
        self.assertEqual(payload["caseCount"], len(payload["cases"]))
        self.assertEqual(["증상", "원인", "해결 방법", "추가 고려사항", "적용 버전"], payload["publicDocumentSections"])
        pairs = {(item["expectedCurrentAssessment"], item["expectedPreviewAssessment"]) for item in payload["cases"]}
        self.assertIn(("CURRENT_DEFECT", "PREVIEW_IMPROVED"), pairs)
        self.assertIn(("CURRENT_DEFECT", "PREVIEW_NOT_FOUND"), pairs)
        self.assertIn(("CURRENT_CONFIG_ERROR", "NOT_APPLICABLE"), pairs)


if __name__ == "__main__":
    unittest.main()
