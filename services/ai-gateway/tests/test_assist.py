from __future__ import annotations

import base64
import json
import tempfile
from types import SimpleNamespace
import unittest
from uuid import uuid4

from fastapi.testclient import TestClient

from app.artifacts import ArtifactStore
from app.comprehensive import plan_query
from app.config import Settings
from app.main import create_app
from app.provider import ComprehensiveResponsesRequest, ContextChunk, ImageArtifact
from app.responses import COMPREHENSIVE_SCHEMA, OpenAIResponsesAdapter
from app.store import InvalidBoundaryError, MemoryStore


PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")
CORRELATION = {"X-Correlation-Id": "assist-test-correlation-0001"}


class PlannerTest(unittest.TestCase):
    def test_cloud_branch_is_never_guessed(self) -> None:
        plan = plan_query("가상머신 배포가 실패합니다")
        self.assertEqual("NEEDS_INFORMATION", plan.state)
        self.assertIn("브랜치", plan.questions_needed[0])

    def test_multi_domain_plan_is_deterministic(self) -> None:
        plan = plan_query("europa VM의 RBD 스토리지 마이그레이션을 확인해줘")
        self.assertEqual("READY", plan.state)
        self.assertEqual(("CLOUD_EUROPA", "WALL_MAIN", "QEMU_EXEC_TOOLS_MAIN"), plan.profile_ids)


class ArtifactTest(unittest.TestCase):
    def test_store_validates_and_deletes_png(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            store = ArtifactStore(root, retention_hours=1, max_bytes=1024 * 1024)
            record = store.put("screen.png", "image/png", PNG)
            self.assertEqual((1, 1), (record.width, record.height))
            self.assertEqual(PNG, store.image(record.artifact_id).data)
            self.assertTrue(store.delete(record.artifact_id))

    def test_media_type_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            store = ArtifactStore(root, retention_hours=1, max_bytes=1024 * 1024)
            with self.assertRaises(InvalidBoundaryError):
                store.put("screen.jpg", "image/jpeg", PNG)

    def test_raw_upload_metadata_and_delete_api(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            settings = Settings(artifact_root=root)
            client = TestClient(create_app(settings, MemoryStore()))
            response = client.post("/v1/artifacts", content=PNG, headers={**CORRELATION, "Content-Type": "image/png", "X-Artifact-Filename": "screen.png", "X-Artifact-Classification": "D0"})
            self.assertEqual(201, response.status_code, response.text)
            artifact_id = response.json()["data"]["artifactId"]
            metadata = client.get(f"/v1/artifacts/{artifact_id}", headers=CORRELATION)
            self.assertEqual("image/png", metadata.json()["data"]["mediaType"])
            deleted = client.delete(f"/v1/artifacts/{artifact_id}", headers={**CORRELATION, "Idempotency-Key": "delete-artifact-test-0001"})
            self.assertTrue(deleted.json()["data"]["deleted"])


class _Responses:
    def __init__(self) -> None:
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(
            output_text='{"state":"ANSWERED","summary":"ok","observedFacts":[],"diagnoses":[],"recommendedActions":[],"unknowns":[],"confidence":"HIGH","citationsUsed":["chunk-1"],"artifactEvidence":[{"artifactId":"artifact-1","finding":"visible","region":"all"}],"abstainReason":null}',
            model="gpt-5.6-sol", id="resp", _request_id="req",
        )


class ComprehensiveOpenAITest(unittest.TestCase):
    def test_image_is_original_detail_and_storage_tools_are_disabled(self) -> None:
        responses = _Responses()
        adapter = OpenAIResponsesAdapter("unused", "unused", client=SimpleNamespace(responses=responses))
        context = (ContextChunk("chunk-1", "D0", "ablecloud-team/ablestack-cloud", "ablestack-europa", "a" * 40, "x.java", "code"),)
        artifact = ImageArtifact("artifact-1", "image/png", PNG, "digest")
        result = adapter.generate_comprehensive(ComprehensiveResponsesRequest("query", "question", context, (artifact,), safety_identifier="tf-" + "a" * 61))
        user_content = responses.kwargs["input"][1]["content"]
        text_payload = json.loads(user_content[0]["text"])
        self.assertEqual("artifact-1", text_payload["artifacts"][0]["artifactId"])
        self.assertEqual("original", user_content[1]["detail"])
        self.assertTrue(user_content[1]["image_url"].startswith("data:image/png;base64,"))
        self.assertFalse(responses.kwargs["store"])
        self.assertEqual([], responses.kwargs["tools"])
        self.assertEqual(COMPREHENSIVE_SCHEMA, responses.kwargs["text"]["format"]["schema"])
        self.assertEqual("ANSWERED", result.report["state"])


if __name__ == "__main__":
    unittest.main()
