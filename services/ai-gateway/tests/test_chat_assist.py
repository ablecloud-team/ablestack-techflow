from __future__ import annotations

import json
import unittest
from urllib.parse import urlencode

from fastapi.testclient import TestClient

from app.chat_assist import case_card, parse_chat_event, parse_command
from app.config import Settings
from app.main import create_app
from app.store import MemoryStore


class FakeBot:
    def __init__(self) -> None:
        self.sent: list[tuple[list[str], dict]] = []

    def validate(self, supplied: str) -> None:
        if supplied != "runtime-chat-token":
            from app.store import InvalidBoundaryError
            raise InvalidBoundaryError("bad token")

    def send(self, user_ids: list[str], payload: dict) -> None:
        self.sent.append((user_ids, payload))


class FakeFlows:
    def __init__(self, store: MemoryStore) -> None:
        self.store = store
        self.calls: list[tuple[str, dict]] = []

    def decide(self, decision: str, payload: dict) -> None:
        self.calls.append((decision, payload))
        case_id = self.store.resolve_community_case(payload["caseId"])["caseId"]
        result = self.store.decide_community_case(
            case_id,
            {
                "decision": decision, "reviewer": payload["reviewer"],
                "expectedDraftVersion": payload["expectedDraftVersion"],
                "editedAnswer": payload.get("editedAnswer"), "note": payload.get("note"),
            },
            payload["eventId"] + "-decision",
        )
        if decision == "APPROVE":
            self.store.mark_community_published(
                case_id, {"postId": "901", "postUrl": "https://community.ablecloud.io/d/901/901"},
                payload["eventId"] + "-publish",
            )


def settings() -> Settings:
    return Settings(
        chat_bot_enabled=True,
        chat_bot_token_file="/run/secrets/chat_bot_token",
        chat_reviewer_usernames=("ceo",),
        community_approve_webhook_file="/run/secrets/community_approve_webhook",
        community_reject_webhook_file="/run/secrets/community_reject_webhook",
    )


def form(text: str, *, username: str = "ceo", token: str = "runtime-chat-token", post_id: str = "100") -> bytes:
    return urlencode({
        "token": token, "user_id": "7", "username": username,
        "post_id": post_id, "timestamp": "1700000000", "text": text,
    }).encode()


class ChatParsingTest(unittest.TestCase):
    def test_form_event_and_korean_command(self) -> None:
        event = parse_chat_event("application/x-www-form-urlencoded", form("수정 abcdef12 1 최종 답변입니다"))
        self.assertEqual(("edit", ["abcdef12", "1", "최종 답변입니다"]), parse_command(event))

    def test_interactive_action(self) -> None:
        payload = {
            "payload": json.dumps({
                "token": "runtime-chat-token", "post_id": "200", "callback_id": "community:x:1",
                "user": {"user_id": "7", "username": "ceo"},
                "actions": [{"name": "approve", "value": "approve:abcdef12:1"}],
            })
        }
        event = parse_chat_event("application/x-www-form-urlencoded", urlencode(payload).encode())
        self.assertEqual(("approve", ["abcdef12", "1"]), parse_command(event))

    def test_card_contains_review_actions(self) -> None:
        store = MemoryStore()
        case = store.create_community_case(
            {"discussionId": "901", "discussionUrl": "https://community.ablecloud.io/d/901",
             "title": "Cube 질문", "authorId": "1", "tagSlugs": []},
            {"draftAnswer": "검토할 답변", "answerState": "ANSWERED", "citations": []},
            "chat-card-idempotency-0001", "chat-card-correlation",
        )
        card = case_card(case)
        names = [item["name"] for item in card["attachments"][0]["actions"]]
        self.assertEqual(["detail", "approve", "reject"], names)


class ChatEndpointTest(unittest.TestCase):
    def setUp(self) -> None:
        self.store = MemoryStore()
        self.case = self.store.create_community_case(
            {"discussionId": "901", "discussionUrl": "https://community.ablecloud.io/d/901",
             "title": "Cube 질문", "authorId": "1", "tagSlugs": []},
            {"draftAnswer": "검토할 답변", "answerState": "ANSWERED", "citations": []},
            "chat-endpoint-idempotency-0001", "chat-endpoint-correlation",
        )
        self.bot = FakeBot()
        self.flows = FakeFlows(self.store)
        self.client = TestClient(create_app(
            settings(), store=self.store, chat_bot_client=self.bot, community_flow_client=self.flows,
        ))

    def post(self, body: bytes):
        return self.client.post(
            "/v1/chat/synology/events", content=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    def test_connect_registers_identity_and_lists_pending(self) -> None:
        response = self.post(form("연결"))
        self.assertEqual(200, response.status_code)
        self.assertIn("승인 담당자로 연결", response.json()["text"])
        self.assertEqual("ceo", self.store.list_chat_reviewers()[0]["username"])

    def test_new_case_notifies_connected_reviewer(self) -> None:
        self.post(form("연결"))
        response = self.client.post(
            "/v1/community/cases",
            headers={
                "X-Correlation-Id": "chat-notification-correlation",
                "Idempotency-Key": "chat-notification-idempotency-0001",
            },
            json={
                "discussionId": "902",
                "discussionUrl": "https://community.ablecloud.io/d/902",
                "title": "새 Community 질문",
                "question": "Cube 상태를 어디에서 확인하나요?",
                "authorId": "42",
                "tagSlugs": ["cube"],
                "artifactIds": [],
            },
        )
        self.assertEqual(201, response.status_code)
        self.assertEqual(["7"], self.bot.sent[0][0])
        self.assertIn("새 Community 질문", self.bot.sent[0][1]["text"])
        self.assertEqual(["detail", "reject"], [
            action["name"] for action in self.bot.sent[0][1]["attachments"][0]["actions"]
        ])

    def test_approve_uses_chat_identity_and_publishes(self) -> None:
        reference = str(self.case["caseId"])[:8]
        response = self.post(form(f"승인 {reference} 1", post_id="approve-100"))
        self.assertEqual(200, response.status_code)
        self.assertIn("PUBLISHED", response.json()["text"])
        self.assertEqual("chat:ceo", self.store.get_community_case(self.case["caseId"])["reviewer"])

    def test_unauthorized_username_is_denied(self) -> None:
        response = self.post(form("대기", username="other"))
        self.assertEqual(403, response.status_code)

    def test_general_user_can_submit_technical_question_without_reviewer_rights(self) -> None:
        response = self.post(form("VM 배포 오류의 원인을 알려줘", username="other"))
        self.assertEqual(200, response.status_code)
        self.assertIn("답변을 보류", response.json()["text"])

    def test_bad_token_is_denied_without_detail(self) -> None:
        response = self.post(form("대기", token="wrong"))
        self.assertEqual(403, response.status_code)
        self.assertNotIn("token", response.json()["text"].lower())


if __name__ == "__main__":
    unittest.main()
