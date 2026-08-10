#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import hmac
import importlib.util
import json
from pathlib import Path
import unittest
import urllib.parse

MODULE_PATH = Path(__file__).with_name("gateway.py")
SPEC = importlib.util.spec_from_file_location("gateway", MODULE_PATH)
gateway = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(gateway)


class SignatureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.secret = b"test-secret"
        self.timestamp = "1753930800"
        self.body = b'{"probe":"issue-14"}'
        digest = hmac.new(
            self.secret,
            self.timestamp.encode("ascii") + b"." + self.body,
            hashlib.sha256,
        ).hexdigest()
        self.signature = f"sha256={digest}"

    def test_valid_signature(self) -> None:
        self.assertTrue(
            gateway.signature_is_valid(
                self.secret, self.timestamp, self.body, self.signature
            )
        )

    def test_previous_secret_is_accepted_during_grace_period(self) -> None:
        self.assertTrue(
            gateway.signature_is_valid(
                (b"new-secret", self.secret),
                self.timestamp,
                self.body,
                self.signature,
            )
        )

    def test_retired_secret_is_rejected_after_grace_period(self) -> None:
        self.assertFalse(
            gateway.signature_is_valid(
                (b"new-secret",),
                self.timestamp,
                self.body,
                self.signature,
            )
        )

    def test_modified_body_is_rejected(self) -> None:
        self.assertFalse(
            gateway.signature_is_valid(
                self.secret, self.timestamp, b'{"probe":"changed"}', self.signature
            )
        )

    def test_malformed_signature_is_rejected(self) -> None:
        self.assertFalse(
            gateway.signature_is_valid(
                self.secret, self.timestamp, self.body, "not-a-signature"
            )
        )

    def test_event_id_contract(self) -> None:
        self.assertIsNotNone(gateway.EVENT_ID_PATTERN.fullmatch("issue14:test-1"))
        self.assertIsNone(gateway.EVENT_ID_PATTERN.fullmatch("../invalid"))


class GithubContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.secret = b"github-secret"
        self.organization = "ablecloud-team"
        self.repository = {
            "full_name": "ablecloud-team/ablestack-techflow",
            "html_url": "https://github.com/ablecloud-team/ablestack-techflow",
            "owner": {"login": "ablecloud-team"},
        }
        self.sender = {"login": "tester"}

    def test_github_signature_uses_raw_body_only(self) -> None:
        body = b'{"zen":"test"}'
        digest = hmac.new(self.secret, body, hashlib.sha256).hexdigest()
        self.assertTrue(
            gateway.github_signature_is_valid(
                self.secret, body, f"sha256={digest}"
            )
        )
        self.assertFalse(
            gateway.github_signature_is_valid(
                self.secret, body + b" ", f"sha256={digest}"
            )
        )

    def test_push_is_minimized_and_message_is_rendered(self) -> None:
        payload = {
            "repository": self.repository,
            "sender": self.sender,
            "ref": "refs/heads/main",
            "before": "a" * 40,
            "after": "b" * 40,
            "created": False,
            "deleted": False,
            "forced": False,
            "compare": "https://github.com/ablecloud-team/ablestack-techflow/compare/a...b",
            "commits": [{"id": "1"}, {"id": "2"}],
            "pusher": {"email": "must-not-be-forwarded@example.com"},
        }
        result = gateway.normalize_github_event(
            "push", payload, "delivery-1", self.organization, "2026-07-31T00:00:00Z"
        )
        self.assertEqual(result["eventType"], "github.push")
        self.assertEqual(result["data"]["commitCount"], 2)
        self.assertIn("변경 내용 보기", result["message"]["text"])
        self.assertNotIn("pusher", json.dumps(result))
        self.assertNotIn("email", json.dumps(result))

    def test_nine_allowlisted_repository_branches_map_to_profiles(self) -> None:
        expected = {
            ("ablecloud-team/ablestack-docs", "master"): "SHARED_DOCS",
            ("ablecloud-team/ablestack-cloud", "main"): "CLOUD_MAIN",
            ("ablecloud-team/ablestack-cloud", "ablestack-diplo"): "CLOUD_DIPLO",
            ("ablecloud-team/ablestack-cloud", "ablestack-europa"): "CLOUD_EUROPA",
            ("ablecloud-team/ablestack-wall", "main"): "WALL_MAIN",
            ("ablecloud-team/ablestack-cockpit-plugin", "ablestack-diplo"): "COCKPIT_DIPLO",
            ("ablecloud-team/ablestack-genie", "master"): "GENIE_MASTER",
            ("ablecloud-team/ablestack-kickstart", "master"): "KICKSTART_MASTER",
            ("ablecloud-team/ablestack-qemu-exec-tools", "main"): "QEMU_EXEC_TOOLS_MAIN",
        }
        self.assertEqual(gateway.SOURCE_PROFILE_BY_REPOSITORY_BRANCH, expected)
        for (repository, branch), profile_id in expected.items():
            normalized = {
                "eventId": f"event-{profile_id.lower()}",
                "eventType": "github.push",
                "repository": {"fullName": repository},
                "data": {
                    "ref": f"refs/heads/{branch}",
                    "after": "a" * 40,
                    "deleted": False,
                },
            }
            result = gateway.normalize_source_discovery_event(normalized, "correlation-0001")
            self.assertEqual(result["sourceProfileId"], profile_id)
            self.assertNotIn("message", result)

    def test_unmapped_or_deleted_push_does_not_request_discovery(self) -> None:
        normalized = {
            "eventId": "event-unmapped",
            "eventType": "github.push",
            "repository": {"fullName": "ablecloud-team/ablestack-techflow"},
            "data": {"ref": "refs/heads/main", "after": "a" * 40, "deleted": False},
        }
        self.assertIsNone(
            gateway.normalize_source_discovery_event(normalized, "correlation-0002")
        )
        normalized["repository"]["fullName"] = "ablecloud-team/ablestack-genie"
        normalized["data"]["ref"] = "refs/heads/master"
        normalized["data"]["deleted"] = True
        self.assertIsNone(
            gateway.normalize_source_discovery_event(normalized, "correlation-0003")
        )


class RagContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.organization = "ablecloud-team"
        self.repository = {
            "full_name": "ablecloud-team/ablestack-techflow",
            "html_url": "https://github.com/ablecloud-team/ablestack-techflow",
            "owner": {"login": "ablecloud-team"},
        }
        self.sender = {"login": "tester"}

    def test_discovery_drops_untrusted_fields(self) -> None:
        result = gateway.normalize_rag_event(
            "/techflow/hooks/rag/discovery",
            {"sourceProfileId": "GENIE_MASTER", "commit": "a" * 40,
             "content": "must-not-enter-flow", "token": "secret"},
            "event-1", "correlation-1",
        )
        self.assertEqual(
            {"eventId": "event-1", "correlationId": "correlation-1",
             "sourceProfileId": "GENIE_MASTER", "commit": "a" * 40}, result,
        )

    def test_review_requires_pinned_commit_and_authorized_reviewer(self) -> None:
        payload = {
            "sourceId": "11111111-1111-4111-8111-111111111111",
            "sourceVersionId": "22222222-2222-4222-8222-222222222222",
            "expectedCommit": "b" * 40, "reviewer": "dhslove",
            "decisionNote": "승인된 고정 커밋을 색인합니다.",
        }
        result = gateway.normalize_rag_event(
            "/techflow/hooks/rag/review", payload, "event-2", "correlation-2"
        )
        self.assertEqual("dhslove", result["reviewer"])
        payload["reviewer"] = "activepieces"
        with self.assertRaisesRegex(ValueError, "invalid_review_contract"):
            gateway.normalize_rag_event(
                "/techflow/hooks/rag/review", payload, "event-3", "correlation-3"
            )

    def test_compatibility_withdrawal_and_evaluation_contracts(self) -> None:
        member = "33333333-3333-4333-8333-333333333333"
        compatibility = gateway.normalize_rag_event(
            "/techflow/hooks/rag/compatibility",
            {"name": "ABLESTACK baseline", "productVersion": "main",
             "reviewer": "dhslove", "members": [{"sourceVersionId": member}]},
            "event-4", "correlation-4",
        )
        self.assertEqual(member, compatibility["members"][0]["sourceVersionId"])
        withdrawal = gateway.normalize_rag_event(
            "/techflow/hooks/rag/withdraw",
            {"sourceId": member, "reviewer": "dhslove", "reason": "승인된 소스 철회 및 파생 삭제"},
            "event-5", "correlation-5",
        )
        self.assertEqual("dhslove", withdrawal["reviewer"])
        evaluation = gateway.normalize_rag_event(
            "/techflow/hooks/rag/evaluation",
            {"name": "GENIE regression", "sourceProfileId": "GENIE_MASTER", "question": "drop me"},
            "event-6", "correlation-6",
        )
        self.assertNotIn("question", evaluation)

    def test_branch_delete_uses_repository_url(self) -> None:
        payload = {
            "repository": self.repository,
            "sender": self.sender,
            "ref": "refs/heads/old",
            "before": "a" * 40,
            "after": "0" * 40,
            "deleted": True,
            "commits": [],
        }
        result = gateway.normalize_github_event(
            "push", payload, "delivery-2", self.organization, "2026-07-31T00:00:00Z"
        )
        self.assertEqual(result["data"]["url"], self.repository["html_url"])

    def test_merged_pull_request_is_rendered(self) -> None:
        payload = {
            "action": "closed",
            "repository": self.repository,
            "sender": self.sender,
            "pull_request": {
                "number": 19,
                "title": "Webhook 자동화",
                "html_url": "https://github.com/ablecloud-team/ablestack-techflow/pull/19",
                "merged": True,
                "merged_at": "2026-07-31T00:00:00Z",
                "merged_by": {"login": "merger"},
                "head": {"ref": "feature/webhook"},
                "base": {"ref": "main"},
            },
        }
        result = gateway.normalize_github_event(
            "pull_request",
            payload,
            "delivery-3",
            self.organization,
            "2026-07-31T00:00:00Z",
        )
        self.assertEqual(result["eventType"], "github.pull_request.merged")
        self.assertEqual(result["data"]["number"], 19)
        self.assertIn("PR 보기", result["message"]["text"])

    def test_pull_request_number_falls_back_to_top_level_payload(self) -> None:
        payload = {
            "action": "closed",
            "number": 20,
            "repository": self.repository,
            "sender": self.sender,
            "pull_request": {
                "title": "Top-level PR number",
                "html_url": "https://github.com/ablecloud-team/ablestack-techflow/pull/20",
                "merged": True,
                "merged_at": "2026-07-31T00:00:00Z",
                "merged_by": {"login": "merger"},
                "head": {"ref": "feature/fallback"},
                "base": {"ref": "main"},
            },
        }
        result = gateway.normalize_github_event(
            "pull_request",
            payload,
            "delivery-3b",
            self.organization,
            "2026-07-31T00:00:00Z",
        )
        self.assertEqual(result["data"]["number"], 20)

    def test_closed_unmerged_pull_request_is_ignored(self) -> None:
        payload = {
            "action": "closed",
            "repository": self.repository,
            "sender": self.sender,
            "pull_request": {"merged": False},
        }
        self.assertIsNone(
            gateway.normalize_github_event(
                "pull_request",
                payload,
                "delivery-4",
                self.organization,
                "2026-07-31T00:00:00Z",
            )
        )

    def test_other_organization_is_rejected(self) -> None:
        payload = {
            "repository": {
                "full_name": "other/example",
                "html_url": "https://github.com/other/example",
                "owner": {"login": "other"},
            },
            "sender": self.sender,
        }
        with self.assertRaisesRegex(ValueError, "organization_not_allowed"):
            gateway.normalize_github_event(
                "push",
                payload,
                "delivery-5",
                self.organization,
                "2026-07-31T00:00:00Z",
            )


class ChatContractTests(unittest.TestCase):
    def test_synology_payload_is_form_encoded_json(self) -> None:
        body = gateway.synology_form_payload("테스트 메시지")
        parsed = urllib.parse.parse_qs(body.decode("utf-8"))
        self.assertEqual(json.loads(parsed["payload"][0]), {"text": "테스트 메시지"})

    def test_http_200_success_false_is_failed(self) -> None:
        result, code = gateway.classify_chat_response(
            200, b'{"success":false,"error":{"code":407}}'
        )
        self.assertEqual(result, "failed")
        self.assertEqual(code, "407")

    def test_http_200_success_true_is_succeeded(self) -> None:
        result, code = gateway.classify_chat_response(200, b'{"success":true}')
        self.assertEqual((result, code), ("succeeded", ""))

    def test_invalid_or_non_2xx_response_is_failed(self) -> None:
        self.assertEqual(
            gateway.classify_chat_response(200, b"not-json"),
            ("failed", "invalid_response"),
        )
        self.assertEqual(
            gateway.classify_chat_response(503, b'{"success":true}'),
            ("failed", "http_error"),
        )

    def test_chat_delivery_slot_uses_millisecond_lease(self) -> None:
        client = object.__new__(gateway.RedisClient)
        calls = []
        client._command = lambda *parts: calls.append(parts) or "OK"

        reserved = client.reserve_milliseconds(
            "synology-chat", 15000, "chat-delivery-slot"
        )

        self.assertTrue(reserved)
        self.assertEqual(calls[0][0], "SET")
        self.assertEqual(calls[0][-2:], ("PX", "15000"))


if __name__ == "__main__":
    unittest.main()
