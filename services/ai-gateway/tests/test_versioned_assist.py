from __future__ import annotations

import json
from pathlib import Path
import unittest

from app.versioned_assist import (
    CURATED_PLATFORM_PROFILE,
    CURRENT_SOURCE_PROFILES,
    INTERNAL_REFERENCE_ONLY_PROFILE,
    PREVIEW_SOURCE_PROFILE,
    VERSIONED_SOURCE_PROFILES,
    coverage_payload,
    expand_retrieval_question,
    format_public_answer,
    projection_is_safe,
    relevant_results,
    sanitize_public_text,
    select_context_results,
    versioned_plan,
)
from app.platform_references import curated_platform_results


class VersionedAssistPolicyTest(unittest.TestCase):
    def test_plan_reviews_docs_diplo_related_code_and_europa_preview(self) -> None:
        plan = versioned_plan("VM 배포가 실패합니다")
        self.assertEqual(list(VERSIONED_SOURCE_PROFILES), plan["sourceProfileIds"])
        self.assertIn("SHARED_DOCS", CURRENT_SOURCE_PROFILES)
        self.assertIn("CLOUD_DIPLO", CURRENT_SOURCE_PROFILES)
        self.assertEqual("CLOUD_EUROPA", PREVIEW_SOURCE_PROFILE)
        self.assertIn(CURATED_PLATFORM_PROFILE, plan["sourceProfileIds"])
        self.assertNotIn(INTERNAL_REFERENCE_ONLY_PROFILE, plan["sourceProfileIds"])

    def test_coverage_records_every_reviewed_profile(self) -> None:
        coverage = coverage_payload("VM 배포 오류", {
            "SHARED_DOCS": [{"chunkId": "1", "content": "VM 배포 절차", "path": "guide.md"}],
            "CLOUD_DIPLO": [],
        })
        self.assertEqual(len(VERSIONED_SOURCE_PROFILES), len(coverage))
        self.assertEqual("EVIDENCE_FOUND", coverage[0]["state"])
        self.assertEqual("NO_RELEVANT_EVIDENCE", coverage[1]["state"])

    def test_console_connecting_question_expands_retrieval_vocabulary(self) -> None:
        question = "Mold 콘솔 화면이 연결중에서 멈춥니다."
        expanded = expand_retrieval_question(question)
        self.assertIn(question, expanded)
        self.assertIn("consoleproxy", expanded)
        self.assertIn("websockify", expanded)
        self.assertIn("VNC".casefold(), expanded.casefold())

    def test_console_connecting_question_prioritizes_console_proxy_evidence(self) -> None:
        question = "가상머신 콘솔 화면이 연결중이라고 표시됩니다."
        rows = [
            {"path": "ui/src/GenericVm.vue", "content": "가상머신 화면 표시"},
            {"path": "systemvm/agent/noVNC/vnc_lite.html", "content": "Connecting websocket websockify VNC"},
            {"path": "docs/systemvm.md", "content": "Console Proxy VM and noVNC console"},
        ]
        ranked = relevant_results(question, rows)
        self.assertEqual("systemvm/agent/noVNC/vnc_lite.html", ranked[0]["path"])

    def test_console_context_includes_multiple_docs_and_current_code_chunks(self) -> None:
        question = "Mold 콘솔 화면이 연결중에서 멈춥니다."
        rows = [{"path": f"consoleproxy/{index}.java", "content": "noVNC websockify VNC"} for index in range(6)]
        selected = select_context_results(question, {
            "SHARED_DOCS": rows,
            "CLOUD_DIPLO": rows,
            CURATED_PLATFORM_PROFILE: curated_platform_results(question),
            "CLOUD_EUROPA": rows,
        })
        self.assertEqual(13, len(selected))
        self.assertEqual(4, sum(item.get("sourceProfileId") == CURATED_PLATFORM_PROFILE for item in selected))

    def test_console_question_loads_only_local_approved_platform_references(self) -> None:
        question = "Mold 콘솔 화면이 연결중 상태입니다."
        results = curated_platform_results(question)
        self.assertEqual(4, len(results))
        self.assertTrue(all(item["sourceProfileId"] == CURATED_PLATFORM_PROFILE for item in results))
        self.assertTrue(any(item["sourceKind"] == "OPERATOR_APPROVED_KNOWLEDGE" for item in results))
        self.assertTrue(any("query-vnc" in item["content"] for item in results))
        self.assertTrue(any("라이브 마이그레이션" in item["content"] for item in results))
        self.assertEqual([], curated_platform_results("사용자 계정 이름을 변경하는 방법"))

    def test_runtime_issue_public_projection_does_not_expose_reference_locator(self) -> None:
        citation = curated_platform_results("Mold 콘솔 화면이 연결중 상태입니다.")[0]
        result = {
            "state": "ANSWERED",
            "report": {
                "summary": "콘솔은 연결중이지만 게스트 서비스는 동작합니다.",
                "observedFacts": [],
                "diagnoses": [{"title": "QEMU VNC 세션 상태 문제"}],
                "recommendedActions": ["sudo virsh qemu-monitor-command <VM> --pretty query-vnc로 확인합니다."],
                "unknowns": [],
                "currentAssessment": "CURRENT_RUNTIME_ISSUE",
                "previewAssessment": "NOT_APPLICABLE",
                "previewGuidance": None,
            },
            "citations": [citation],
        }
        answer = format_public_answer(result) or ""
        self.assertIn("가상화 런타임 상태 문제", answer)
        self.assertNotIn("operator://", answer)
        self.assertNotIn("sourceLocator", answer)
        self.assertTrue(projection_is_safe(answer), answer)

    def test_public_projection_removes_all_external_urls(self) -> None:
        answer = sanitize_public_text(
            "공식 자료 https://www.qemu.org/docs/master/interop/qemu-qmp-ref.html 를 확인합니다.",
        )
        self.assertNotIn("https://", answer)
        self.assertIn("내부 검토 자료", answer)

    def test_public_projection_removes_inline_citation_tokens_without_placeholder(self) -> None:
        token = "81e47d5d-d194-5b62-9979-55a767d9a91a"
        answer = sanitize_public_text(
            f"QEMU 상태를 확인합니다. [{token}] 다음 조치를 수행합니다. [{token}]",
            [{"chunkId": token}],
        )
        self.assertEqual("QEMU 상태를 확인합니다. 다음 조치를 수행합니다.", answer)
        self.assertNotIn("내부 근거", answer)

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

    def test_public_projection_does_not_replace_branch_name_inside_normal_word(self) -> None:
        answer = sanitize_public_text("DNS Domain Name Suffix를 확인합니다.", [{"branch": "main"}])
        self.assertEqual("DNS Domain Name Suffix를 확인합니다.", answer)

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
        self.assertIn(("CURRENT_RUNTIME_ISSUE", "NOT_APPLICABLE"), pairs)
        console = next(item for item in payload["cases"] if item["caseKey"] == "MOLD-CONSOLE-CONNECTING-001")
        self.assertEqual("Mold에서 가상머신의 콘솔 보기를 클릭하면 콘솔 화면이 표시되지만 \"연결중\"이라고 표시되고, 더 이상 화면을 보여주지 않습니다. 콘솔을 보려면 어떻게 해야 하나요?", console["question"])
        self.assertIn("query-vnc", console["requiredPublicGuidance"])


if __name__ == "__main__":
    unittest.main()
