#!/usr/bin/env python3
"""Poll new unanswered Flarum discussions and send normalized D0 events to Activepieces."""

from __future__ import annotations

from html.parser import HTMLParser
import json
import mimetypes
import os
from pathlib import Path
import re
import tempfile
import time
import urllib.parse
import urllib.error
import urllib.request
from uuid import uuid4


DEFAULT_ATTACHMENT_MAX_BYTES = 1024 * 1024 * 1024
DEFAULT_ARCHIVE_MAX_BYTES = 10 * 1024 * 1024 * 1024
DEFAULT_ATTACHMENT_TIMEOUT_SECONDS = 7200
DEFAULT_ATTACHMENT_RETRIES = 2
DOWNLOAD_CHUNK_BYTES = 1024 * 1024
TRANSIENT_HTTP_STATUSES = {408, 425, 429, 500, 502, 503, 504}


class ContentParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.text: list[str] = []
        self.links: list[str] = []

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.text.append(data.strip())

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.append(href)


def read_secret(name: str) -> str:
    return Path(os.environ[name]).read_text(encoding="utf-8").strip()


def request_json(
    url: str, *, token: str | None = None, data: dict | None = None, extra_headers: dict[str, str] | None = None
) -> dict:
    body = json.dumps(data, ensure_ascii=False).encode("utf-8") if data is not None else None
    headers = {"Accept": "application/vnd.api+json"}
    if token:
        headers["Authorization"] = f"Token {token}"
    if body is not None:
        headers["Content-Type"] = "application/json"
    headers.update(extra_headers or {})
    with urllib.request.urlopen(urllib.request.Request(url, data=body, headers=headers), timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _bounded_env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc
    if not minimum <= value <= maximum:
        raise RuntimeError(f"{name} must be between {minimum} and {maximum}")
    return value


def _attachment_policy() -> tuple[int, int, int, int]:
    return (
        _bounded_env_int(
            "TECHFLOW_COMMUNITY_ATTACHMENT_MAX_BYTES", DEFAULT_ATTACHMENT_MAX_BYTES,
            1024, DEFAULT_ATTACHMENT_MAX_BYTES,
        ),
        _bounded_env_int(
            "TECHFLOW_COMMUNITY_ARCHIVE_MAX_BYTES", DEFAULT_ARCHIVE_MAX_BYTES,
            DEFAULT_ATTACHMENT_MAX_BYTES, DEFAULT_ARCHIVE_MAX_BYTES,
        ),
        _bounded_env_int(
            "TECHFLOW_COMMUNITY_ATTACHMENT_TIMEOUT_SECONDS", DEFAULT_ATTACHMENT_TIMEOUT_SECONDS,
            5, DEFAULT_ATTACHMENT_TIMEOUT_SECONDS,
        ),
        _bounded_env_int("TECHFLOW_COMMUNITY_ATTACHMENT_RETRIES", DEFAULT_ATTACHMENT_RETRIES, 0, 3),
    )


def _attachment_filename(content_disposition: str, path: str) -> str:
    encoded = re.search(r"filename\*=UTF-8''([^;]+)", content_disposition, re.IGNORECASE)
    quoted = re.search(r'filename="([^"]+)"', content_disposition, re.IGNORECASE)
    value = urllib.parse.unquote(encoded.group(1)) if encoded else (quoted.group(1) if quoted else Path(path).name)
    return Path(value.replace("\\", "/")).name[:128] or "community-artifact"


def _warning(filename: str, reason: str) -> str:
    safe_name = Path(filename.replace("\\", "/")).name[:80] or "첨부파일"
    messages = {
        "size": f"첨부파일 {safe_name}이 허용 크기(일반 1GiB, 압축 10GiB)를 초과해 분석하지 않았습니다.",
        "unsafe": f"첨부파일 {safe_name}은 지원하지 않거나 안전 검사를 통과하지 못해 분석에서 제외했습니다.",
        "fetch": f"첨부파일 {safe_name}을 가져오지 못했습니다. 잠시 후 다시 첨부해 주세요.",
        "origin": f"첨부파일 {safe_name}은 Community 외부 주소이므로 분석하지 않았습니다.",
    }
    return messages[reason]


def _normalized_attachment_media_type(filename: str, media_type: str) -> str:
    if media_type not in {"application/force-download", "application/octet-stream"}:
        return media_type
    lowered = filename.casefold()
    if lowered.endswith(".zip"):
        return "application/zip"
    if lowered.endswith((".tar.gz", ".tgz", ".gz")):
        return "application/gzip"
    if lowered.endswith((".log", ".txt", ".csv", ".ini")):
        return "text/plain"
    return mimetypes.guess_type(filename)[0] or media_type


def _is_archive(filename: str, media_type: str) -> bool:
    normalized = _normalized_attachment_media_type(filename, media_type)
    return normalized in {"application/zip", "application/gzip", "application/x-gzip"}


def _read_attachment(
    request: urllib.request.Request, destination: Path, *, filename: str,
    max_bytes: int, max_archive_bytes: int, timeout: int, retries: int,
) -> tuple[int, str, str, str]:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        destination.unlink(missing_ok=True)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                media_type = response.headers.get_content_type()
                disposition = response.headers.get("Content-Disposition") or ""
                resolved_name = _attachment_filename(disposition, urllib.parse.urlparse(request.full_url).path) or filename
                limit = max_archive_bytes if _is_archive(resolved_name, media_type) else max_bytes
                content_length = response.headers.get("Content-Length")
                if content_length and int(content_length) > limit:
                    raise ValueError("size")
                total = 0
                with destination.open("xb") as target:
                    while True:
                        chunk = response.read(DOWNLOAD_CHUNK_BYTES)
                        if not chunk:
                            break
                        total += len(chunk)
                        if total > limit:
                            raise ValueError("size")
                        target.write(chunk)
                return total, media_type, disposition, resolved_name
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code not in TRANSIENT_HTTP_STATUSES or attempt >= retries:
                raise
        except urllib.error.URLError as exc:
            last_error = exc
            if attempt >= retries:
                raise
        if attempt < retries:
            time.sleep(min(2 ** attempt, 2))
    assert last_error is not None
    raise last_error


def _file_chunks(path: Path):
    with path.open("rb") as source:
        while chunk := source.read(DOWNLOAD_CHUNK_BYTES):
            yield chunk


def _upload_artifact(
    gateway_url: str, path: Path, filename: str, media_type: str, correlation: str, timeout: int,
) -> str:
    upload = urllib.request.Request(
        gateway_url.rstrip("/") + "/v1/artifacts", data=_file_chunks(path), method="POST",
        headers={"Content-Type": media_type, "Content-Length": str(path.stat().st_size),
                 "X-Artifact-Filename": filename, "X-Artifact-Classification": "D0",
                 "X-Correlation-Id": correlation},
    )
    with urllib.request.urlopen(upload, timeout=timeout) as response:
        return str(json.loads(response.read().decode("utf-8"))["data"]["artifactId"])


def normalize(payload: dict, base_url: str) -> list[dict]:
    included = {(item["type"], item["id"]): item for item in payload.get("included") or []}
    events = []
    for discussion in payload.get("data") or []:
        attrs = discussion.get("attributes") or {}
        if int(attrs.get("commentCount") or 0) != 1:
            continue
        relationships = discussion.get("relationships") or {}
        post_ref = ((relationships.get("firstPost") or {}).get("data") or {})
        user_ref = ((relationships.get("user") or {}).get("data") or {})
        tag_refs = ((relationships.get("tags") or {}).get("data") or [])
        post = included.get((post_ref.get("type"), post_ref.get("id")), {})
        user = included.get((user_ref.get("type"), user_ref.get("id")), {})
        parser = ContentParser()
        parser.feed((post.get("attributes") or {}).get("contentHtml") or "")
        events.append({
            "discussionId": str(discussion["id"]),
            "discussionUrl": f"{base_url}/d/{discussion['id']}",
            "title": attrs.get("title") or "Community question",
            "question": "\n".join(parser.text)[:4000],
            "authorId": str(user_ref.get("id") or (user.get("attributes") or {}).get("username") or "unknown"),
            "tagSlugs": [
                (included.get((ref.get("type"), ref.get("id")), {}).get("attributes") or {}).get("slug")
                for ref in tag_refs
                if (included.get((ref.get("type"), ref.get("id")), {}).get("attributes") or {}).get("slug")
            ],
            "attachmentUrls": parser.links[:5],
        })
    return events


def upload_artifacts(
    event: dict, gateway_url: str, base_url: str, public_url: str, token: str, correlation: str
) -> list[str]:
    ids: list[str] = []
    warnings: list[str] = list(event.get("artifactWarnings") or [])
    max_bytes, max_archive_bytes, timeout, retries = _attachment_policy()
    temp_root = Path(os.getenv(
        "TECHFLOW_COMMUNITY_ATTACHMENT_TMP_DIR", str(Path(tempfile.gettempdir()) / "techflow-community-poller")
    ))
    temp_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    for raw_url in event.pop("attachmentUrls", []):
        public_attachment_url = urllib.parse.urljoin(public_url + "/", raw_url)
        parsed = urllib.parse.urlparse(public_attachment_url)
        if parsed.scheme != "https" or parsed.netloc != urllib.parse.urlparse(public_url).netloc:
            warnings.append(_warning(Path(parsed.path).name, "origin"))
            continue
        internal_url = urllib.parse.urljoin(base_url + "/", parsed.path.lstrip("/"))
        if parsed.query:
            internal_url = f"{internal_url}?{parsed.query}"
        req = urllib.request.Request(internal_url, headers={"Authorization": f"Token {token}"})
        filename = Path(parsed.path).name or "community-artifact"
        with tempfile.NamedTemporaryFile(prefix="attachment-", suffix=".part", dir=temp_root, delete=False) as holder:
            temporary = Path(holder.name)
        temporary.unlink(missing_ok=True)
        try:
            try:
                _, media_type, disposition, filename = _read_attachment(
                    req, temporary, filename=filename, max_bytes=max_bytes,
                    max_archive_bytes=max_archive_bytes, timeout=timeout, retries=retries,
                )
                filename = _attachment_filename(disposition, parsed.path)
            except ValueError as exc:
                if str(exc) == "size":
                    warnings.append(_warning(filename, "size"))
                    continue
                raise
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
                warnings.append(_warning(filename, "fetch"))
                continue
            media_type = _normalized_attachment_media_type(filename, media_type)
            try:
                ids.append(_upload_artifact(gateway_url, temporary, filename, media_type, correlation, timeout))
            except urllib.error.HTTPError as exc:
                if exc.code in TRANSIENT_HTTP_STATUSES:
                    warnings.append(_warning(filename, "fetch"))
                else:
                    warnings.append(_warning(filename, "unsafe"))
            except (urllib.error.URLError, TimeoutError):
                warnings.append(_warning(filename, "fetch"))
        finally:
            temporary.unlink(missing_ok=True)
    event["artifactWarnings"] = warnings
    return ids


def run_once(state_path: Path, *, bootstrap_only: bool = False) -> dict:
    base_url = os.getenv("TECHFLOW_FLARUM_BASE_URL", "https://community.ablecloud.io").rstrip("/")
    public_url = os.getenv("TECHFLOW_FLARUM_PUBLIC_URL", "https://community.ablecloud.io").rstrip("/")
    gateway_url = os.getenv("TECHFLOW_GATEWAY_URL", "http://gateway:8090")
    token = read_secret("TECHFLOW_FLARUM_API_KEY_FILE")
    webhook = read_secret("TECHFLOW_COMMUNITY_INGEST_WEBHOOK_FILE")
    api_url = base_url + "/api/discussions?sort=-createdAt&include=user,tags,firstPost&page%5Blimit%5D=50"
    events = normalize(request_json(api_url, token=token), public_url)
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {"seen": []}
    seen = set(state.get("seen") or [])
    delivered = 0
    for event in reversed(events):
        discussion_id = event["discussionId"]
        if discussion_id in seen:
            continue
        seen.add(discussion_id)
        if bootstrap_only:
            continue
        correlation = f"community-{discussion_id}-{uuid4().hex[:12]}"
        event["correlationId"] = correlation
        event["eventId"] = f"flarum-discussion-{discussion_id}"
        event["artifactIds"] = upload_artifacts(event, gateway_url, base_url, public_url, token, correlation)
        request_json(webhook, data=event)
        delivered += 1
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps({"seen": sorted(seen, key=int)[-1000:]}, separators=(",", ":")), encoding="utf-8")
    reconcile_id = uuid4().hex
    reconciliation = request_json(
        gateway_url.rstrip("/") + "/v1/community/reviews/reconcile",
        data={},
        extra_headers={"X-Correlation-Id": f"community-reconcile-{reconcile_id}", "Idempotency-Key": f"community-reconcile-{reconcile_id}"},
    )
    return {
        "observed": len(events), "delivered": delivered, "seen": len(seen),
        "reviewsChecked": reconciliation.get("data", {}).get("checked", 0),
        "reviewsApproved": reconciliation.get("data", {}).get("approved", 0),
        "reviewsRetried": reconciliation.get("data", {}).get("retried", 0),
        "reviewRetryFailed": reconciliation.get("data", {}).get("retryFailed", 0),
    }


def main() -> int:
    state_path = Path(os.getenv("TECHFLOW_COMMUNITY_POLLER_STATE", "/var/lib/techflow-community-poller/state.json"))
    first = not state_path.exists()
    interval = max(10, int(os.getenv("TECHFLOW_COMMUNITY_POLL_INTERVAL_SECONDS", "10")))
    once = os.getenv("TECHFLOW_COMMUNITY_POLL_ONCE", "false").lower() == "true"
    while True:
        try:
            result = run_once(state_path, bootstrap_only=first)
            print(json.dumps({"event": "community_poll_completed", **result}, separators=(",", ":")), flush=True)
            first = False
        except Exception as exc:
            print(json.dumps({"event": "community_poll_failed", "errorType": type(exc).__name__}), flush=True)
        if once:
            return 0
        time.sleep(interval)


if __name__ == "__main__":
    raise SystemExit(main())
