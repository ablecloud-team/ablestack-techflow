"""Flarum Community draft formatting and approved-only publishing boundary."""

from __future__ import annotations

import json
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from .store import InvalidBoundaryError


TAG_PROFILE_MAP = {
    "mold": "CLOUD_EUROPA",
    "ablestack-vm": "CLOUD_EUROPA",
    "vm-manage": "CLOUD_EUROPA",
    "cube": "SHARED_DOCS",
    "ablestack": "SHARED_DOCS",
    "ablestack-hci": "SHARED_DOCS",
    "ablestack-error": "SHARED_DOCS",
    "ablestack-v4-x-diplo": "SHARED_DOCS",
}


def profiles_for_tags(tag_slugs: list[str]) -> list[str]:
    profiles = []
    for slug in tag_slugs:
        profile = TAG_PROFILE_MAP.get(slug)
        if profile and profile not in profiles:
            profiles.append(profile)
    return profiles or ["SHARED_DOCS"]


def citation_url(citation: dict[str, Any]) -> str:
    repository = citation["repository"]
    commit = citation["commit"]
    path = citation["path"]
    start = citation["startLine"]
    end = citation["endLine"]
    return f"https://github.com/{repository}/blob/{commit}/{path}#L{start}-L{end}"


def format_draft(result: dict[str, Any]) -> str | None:
    if result.get("state") != "ANSWERED" or not result.get("report"):
        return None
    report = result["report"]
    lines = ["## AI 답변 초안", "", report.get("summary", "").strip()]
    for heading, key in (("확인된 내용", "observedFacts"), ("가능한 원인", "diagnoses"), ("권장 확인 사항", "recommendedActions")):
        rows = report.get(key) or []
        if rows:
            lines.extend(["", f"### {heading}"])
            for row in rows:
                if isinstance(row, str):
                    text = row
                else:
                    text = row.get("text") or row.get("title") or row.get("action") or row.get("finding") or ""
                if text:
                    lines.append(f"- {text}")
    citations = result.get("citations") or []
    if citations:
        lines.extend(["", "### 근거"])
        for item in citations:
            label = f"{item['repository']} · {item['path']}:{item['startLine']}-{item['endLine']}"
            lines.append(f"- [{label}]({citation_url(item)})")
    lines.extend(["", "> 이 답변은 ABLESTACK TechFlow가 생성하고 담당자가 검토·승인했습니다."])
    return "\n".join(lines).strip()


class FlarumClient:
    def __init__(self, base_url: str, public_url: str, api_key_file: str | None, enabled: bool) -> None:
        self.base_url = base_url.rstrip("/")
        self.public_url = public_url.rstrip("/")
        self.api_key_file = api_key_file
        self.enabled = enabled

    def _request(self, path: str, method: str = "GET", body: bytes | None = None) -> dict[str, Any]:
        if not self.enabled or not self.api_key_file:
            raise InvalidBoundaryError("community publishing is disabled")
        key = Path(self.api_key_file).read_text(encoding="utf-8").strip()
        if len(key) != 40:
            raise InvalidBoundaryError("invalid Flarum API key boundary")
        request = urllib.request.Request(
            f"{self.base_url}{path}", data=body, method=method,
            headers={"Authorization": f"Token {key}", "Content-Type": "application/json", "Accept": "application/vnd.api+json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError("Flarum request failed") from exc

    def publish_reply(self, discussion_id: str, answer: str, marker: str) -> dict[str, Any]:
        query = urllib.parse.urlencode({"filter[discussion]": discussion_id, "page[limit]": "50"})
        existing = self._request(f"/api/posts?{query}")
        for item in existing.get("data") or []:
            attributes = item.get("attributes") or {}
            if marker in (attributes.get("contentHtml") or "") or marker in (attributes.get("content") or ""):
                post_id = str(item["id"])
                return {"postId": post_id, "postUrl": f"{self.public_url}/d/{discussion_id}/{post_id}", "reused": True}
        body = json.dumps({
            "data": {
                "type": "posts",
                "attributes": {"content": f"{answer}\n\n{marker}"},
                "relationships": {"discussion": {"data": {"type": "discussions", "id": discussion_id}}},
            }
        }, ensure_ascii=False).encode("utf-8")
        payload = self._request("/api/posts", "POST", body)
        post_id = str(payload["data"]["id"])
        return {"postId": post_id, "postUrl": f"{self.public_url}/d/{discussion_id}/{post_id}", "reused": False}
