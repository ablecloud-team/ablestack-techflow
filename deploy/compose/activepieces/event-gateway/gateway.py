#!/usr/bin/env python3
"""Fail-closed TechFlow Webhook ingress and internal Chat adapter."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

EVENT_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
SIGNATURE_PATTERN = re.compile(r"^sha256=([0-9a-fA-F]{64})$")
CONTROL_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

SOURCE_PROFILE_BY_REPOSITORY_BRANCH = {
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


def required_env(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def int_env(name: str, default: int, minimum: int) -> int:
    value = int(os.environ.get(name, str(default)))
    if value < minimum:
        raise RuntimeError(f"{name} must be at least {minimum}")
    return value


class Config:
    def __init__(self) -> None:
        self.listen_host = os.environ.get("TECHFLOW_WEBHOOK_LISTEN_HOST", "0.0.0.0")
        self.listen_port = int_env("TECHFLOW_WEBHOOK_LISTEN_PORT", 8081, 1)
        self.path_prefix = os.environ.get(
            "TECHFLOW_WEBHOOK_PATH_PREFIX", "/techflow/hooks/"
        )
        current_secret = required_env("TECHFLOW_WEBHOOK_SECRET").encode("utf-8")
        previous_secret = os.environ.get(
            "TECHFLOW_WEBHOOK_SECRET_PREVIOUS", ""
        ).encode("utf-8")
        self.secrets = tuple(
            secret for secret in (current_secret, previous_secret) if secret
        )
        self.max_skew = int_env("TECHFLOW_WEBHOOK_MAX_SKEW_SECONDS", 300, 1)
        self.event_ttl = int_env("TECHFLOW_WEBHOOK_EVENT_TTL_SECONDS", 86400, 60)
        self.body_limit = int_env(
            "TECHFLOW_WEBHOOK_BODY_LIMIT_BYTES", 1048576, 1024
        )
        self.upstream_url = os.environ.get("TECHFLOW_WEBHOOK_UPSTREAM_URL", "")

        self.github_path = os.environ.get(
            "TECHFLOW_GITHUB_WEBHOOK_PATH", "/techflow/hooks/github/chat"
        )
        self.github_organization = os.environ.get(
            "TECHFLOW_GITHUB_ORGANIZATION", "ablecloud-team"
        )
        self.github_secret = os.environ.get(
            "TECHFLOW_GITHUB_WEBHOOK_SECRET", ""
        ).encode("utf-8")
        self.github_upstream_url = os.environ.get(
            "TECHFLOW_GITHUB_UPSTREAM_URL", ""
        )
        self.github_source_upstream_url = os.environ.get(
            "TECHFLOW_GITHUB_SOURCE_UPSTREAM_URL", ""
        )
        self.github_event_ttl = int_env(
            "TECHFLOW_GITHUB_EVENT_TTL_SECONDS", 604800, 60
        )

        self.chat_internal_path = os.environ.get(
            "TECHFLOW_CHAT_INTERNAL_PATH", "/internal/chat/github"
        )
        self.chat_webhook_url = os.environ.get("TECHFLOW_CHAT_WEBHOOK_URL", "")
        self.chat_timeout = int_env("TECHFLOW_CHAT_TIMEOUT_SECONDS", 10, 1)
        self.chat_min_interval_ms = int_env(
            "TECHFLOW_CHAT_MIN_INTERVAL_MILLISECONDS", 600, 500
        )

        self.rag_paths = {
            os.environ.get("TECHFLOW_RAG_DISCOVERY_PATH", "/techflow/hooks/rag/discovery"):
                os.environ.get("TECHFLOW_RAG_DISCOVERY_UPSTREAM_URL", ""),
            os.environ.get("TECHFLOW_RAG_REVIEW_PATH", "/techflow/hooks/rag/review"):
                os.environ.get("TECHFLOW_RAG_REVIEW_UPSTREAM_URL", ""),
            os.environ.get("TECHFLOW_RAG_COMPATIBILITY_PATH", "/techflow/hooks/rag/compatibility"):
                os.environ.get("TECHFLOW_RAG_COMPATIBILITY_UPSTREAM_URL", ""),
            os.environ.get("TECHFLOW_RAG_WITHDRAW_PATH", "/techflow/hooks/rag/withdraw"):
                os.environ.get("TECHFLOW_RAG_WITHDRAW_UPSTREAM_URL", ""),
            os.environ.get("TECHFLOW_RAG_EVALUATION_PATH", "/techflow/hooks/rag/evaluation"):
                os.environ.get("TECHFLOW_RAG_EVALUATION_UPSTREAM_URL", ""),
        }

        self.redis_host = os.environ.get("AP_REDIS_HOST", "redis")
        self.redis_port = int_env("AP_REDIS_PORT", 6379, 1)
        self.redis_password = required_env("AP_REDIS_PASSWORD")


class RedisError(RuntimeError):
    pass


class RedisClient:
    def __init__(self, config: Config) -> None:
        self.host = config.redis_host
        self.port = config.redis_port
        self.password = config.redis_password
        self.timeout = 3

    @staticmethod
    def _encode(parts: list[str]) -> bytes:
        encoded = [f"*{len(parts)}\r\n".encode("ascii")]
        for part in parts:
            value = part.encode("utf-8")
            encoded.append(f"${len(value)}\r\n".encode("ascii"))
            encoded.append(value + b"\r\n")
        return b"".join(encoded)

    @staticmethod
    def _read_line(stream) -> bytes:
        line = stream.readline()
        if not line.endswith(b"\r\n"):
            raise RedisError("Incomplete Redis response")
        return line[:-2]

    def _command(self, *parts: str):
        try:
            with socket.create_connection(
                (self.host, self.port), timeout=self.timeout
            ) as connection:
                connection.settimeout(self.timeout)
                stream = connection.makefile("rwb")
                stream.write(self._encode(["AUTH", self.password]))
                stream.flush()
                auth = self._read_line(stream)
                if auth != b"+OK":
                    raise RedisError("Redis authentication failed")

                stream.write(self._encode(list(parts)))
                stream.flush()
                response = self._read_line(stream)
        except (OSError, TimeoutError) as exc:
            raise RedisError("Redis is unavailable") from exc

        prefix, payload = response[:1], response[1:]
        if prefix == b"+":
            return payload.decode("utf-8")
        if prefix == b":":
            return int(payload)
        if prefix == b"$" and payload == b"-1":
            return None
        if prefix == b"-":
            raise RedisError("Redis command failed")
        raise RedisError("Unsupported Redis response")

    def ping(self) -> bool:
        return self._command("PING") == "PONG"

    @staticmethod
    def _key(namespace: str, event_id: str) -> str:
        key_hash = hashlib.sha256(event_id.encode("utf-8")).hexdigest()
        return f"techflow:webhook:{namespace}:{key_hash}"

    def reserve(self, event_id: str, ttl: int, namespace: str = "event") -> bool:
        return (
            self._command(
                "SET", self._key(namespace, event_id), "1", "NX", "EX", str(ttl)
            )
            == "OK"
        )

    def reserve_milliseconds(
        self, event_id: str, ttl_ms: int, namespace: str
    ) -> bool:
        return (
            self._command(
                "SET",
                self._key(namespace, event_id),
                "1",
                "NX",
                "PX",
                str(ttl_ms),
            )
            == "OK"
        )

    def release(self, event_id: str, namespace: str = "event") -> None:
        self._command("DEL", self._key(namespace, event_id))


def expected_signature(secret: bytes, timestamp: str, body: bytes) -> str:
    message = timestamp.encode("ascii") + b"." + body
    return hmac.new(secret, message, hashlib.sha256).hexdigest()


def signature_is_valid(
    secrets: bytes | tuple[bytes, ...] | list[bytes],
    timestamp: str,
    body: bytes,
    supplied: str,
) -> bool:
    match = SIGNATURE_PATTERN.fullmatch(supplied)
    if not match:
        return False
    candidates = (secrets,) if isinstance(secrets, bytes) else tuple(secrets)
    supplied_digest = match.group(1).lower()
    valid = False
    for secret in candidates:
        expected = expected_signature(secret, timestamp, body)
        valid = hmac.compare_digest(expected, supplied_digest) or valid
    return valid


def github_signature_is_valid(secret: bytes, body: bytes, supplied: str) -> bool:
    match = SIGNATURE_PATTERN.fullmatch(supplied)
    if not match:
        return False
    expected = hmac.new(secret, body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, match.group(1).lower())


def clean_text(value: object, limit: int) -> str:
    text = CONTROL_PATTERN.sub("", str(value or "")).strip()
    return text[:limit]


def github_url(value: object, organization: str) -> str:
    url = clean_text(value, 2048)
    prefix = f"https://github.com/{organization}/"
    return url if url.startswith(prefix) else ""


def normalize_github_event(
    event_name: str,
    payload: dict,
    event_id: str,
    organization: str,
    received_at: str,
) -> dict | None:
    repository = payload.get("repository") or {}
    organization_payload = payload.get("organization") or {}
    owner = repository.get("owner") or {}
    org_login = organization_payload.get("login") or owner.get("login")
    full_name = clean_text(repository.get("full_name"), 256)
    repository_url = github_url(repository.get("html_url"), organization)
    sender = payload.get("sender") or {}
    actor_login = clean_text(sender.get("login") or "unknown", 128)

    if org_login != organization or not full_name.startswith(f"{organization}/"):
        raise ValueError("organization_not_allowed")
    if not repository_url:
        raise ValueError("repository_url_invalid")

    envelope = {
        "contractVersion": "1.0",
        "eventId": event_id,
        "receivedAt": received_at,
        "source": {"provider": "github", "organization": organization},
        "repository": {"fullName": full_name, "url": repository_url},
        "actor": {"login": actor_login},
    }

    if event_name == "push":
        ref = clean_text(payload.get("ref"), 256)
        short_ref = ref.removeprefix("refs/heads/").removeprefix("refs/tags/")
        compare_url = github_url(payload.get("compare"), organization) or repository_url
        commit_count = min(len(payload.get("commits") or []), 10000)
        forced = bool(payload.get("forced"))
        forced_marker = " · force push" if forced else ""
        text = (
            f"[GitHub Push] {full_name} · {short_ref or ref}\n"
            f"{actor_login} · {commit_count} commit(s){forced_marker}\n"
            f"<{compare_url}|변경 내용 보기>"
        )
        envelope.update(
            {
                "eventType": "github.push",
                "data": {
                    "ref": ref,
                    "before": clean_text(payload.get("before"), 64),
                    "after": clean_text(payload.get("after"), 64),
                    "created": bool(payload.get("created")),
                    "deleted": bool(payload.get("deleted")),
                    "forced": forced,
                    "commitCount": commit_count,
                    "url": compare_url,
                },
                "message": {"url": compare_url, "text": clean_text(text, 4000)},
            }
        )
        return envelope

    if event_name == "pull_request":
        pull_request = payload.get("pull_request") or {}
        if payload.get("action") != "closed" or pull_request.get("merged") is not True:
            return None
        pr_url = github_url(pull_request.get("html_url"), organization)
        if not pr_url:
            raise ValueError("pull_request_url_invalid")
        merged_by = pull_request.get("merged_by") or {}
        merged_by_login = clean_text(merged_by.get("login") or actor_login, 128)
        head_ref = clean_text((pull_request.get("head") or {}).get("ref"), 256)
        base_ref = clean_text((pull_request.get("base") or {}).get("ref"), 256)
        title = clean_text(pull_request.get("title"), 512)
        number = pull_request.get("number", payload.get("number"))
        if not isinstance(number, int):
            raise ValueError("pull_request_number_invalid")
        text = (
            f"[GitHub PR Merge] {full_name} #{number}\n"
            f"{title}\n"
            f"{merged_by_login} · {head_ref} → {base_ref}\n"
            f"<{pr_url}|PR 보기>"
        )
        envelope.update(
            {
                "eventType": "github.pull_request.merged",
                "data": {
                    "number": number,
                    "title": title,
                    "url": pr_url,
                    "baseRef": base_ref,
                    "headRef": head_ref,
                    "mergedAt": clean_text(pull_request.get("merged_at"), 64),
                    "mergedBy": merged_by_login,
                },
                "message": {"url": pr_url, "text": clean_text(text, 4000)},
            }
        )
        return envelope

    raise ValueError("event_not_allowed")


def normalize_source_discovery_event(normalized: dict, correlation_id: str) -> dict | None:
    if normalized.get("eventType") != "github.push":
        return None
    data = normalized.get("data") or {}
    if data.get("deleted") is True:
        return None
    ref = clean_text(data.get("ref"), 256)
    branch_prefix = "refs/heads/"
    if not ref.startswith(branch_prefix):
        return None
    branch = ref[len(branch_prefix):]
    repository = clean_text((normalized.get("repository") or {}).get("fullName"), 256)
    profile_id = SOURCE_PROFILE_BY_REPOSITORY_BRANCH.get((repository, branch))
    commit = clean_text(data.get("after"), 40)
    if not profile_id or not COMMIT_PATTERN.fullmatch(commit):
        return None
    return {
        "contractVersion": "1.0",
        "eventType": "source.discovery.requested",
        "eventId": normalized["eventId"],
        "correlationId": correlation_id,
        "sourceProfileId": profile_id,
        "repository": repository,
        "branch": branch,
        "commit": commit,
        "detectedBy": "activepieces-github",
    }


def normalize_rag_event(path: str, payload: object, event_id: str, correlation_id: str) -> dict:
    """Validate and minimize authenticated orchestration data before AP stores it."""
    if not isinstance(payload, dict):
        raise ValueError("body_must_be_object")
    common = {"eventId": event_id, "correlationId": correlation_id}

    if path.endswith("/discovery"):
        profile = payload.get("sourceProfileId")
        commit = payload.get("commit")
        if profile not in SOURCE_PROFILE_BY_REPOSITORY_BRANCH.values():
            raise ValueError("invalid_source_profile")
        if commit is not None and (not isinstance(commit, str) or not COMMIT_PATTERN.fullmatch(commit)):
            raise ValueError("invalid_commit")
        return {**common, "sourceProfileId": profile, "commit": commit}

    if path.endswith("/review"):
        values = [payload.get(key) for key in ("sourceId", "sourceVersionId", "expectedCommit", "reviewer", "decisionNote")]
        if not all(isinstance(value, str) for value in values):
            raise ValueError("invalid_review_contract")
        source_id, version_id, commit, reviewer, note = values
        if not UUID_PATTERN.fullmatch(source_id) or not UUID_PATTERN.fullmatch(version_id):
            raise ValueError("invalid_source_identifier")
        if not COMMIT_PATTERN.fullmatch(commit) or reviewer != "dhslove" or not 10 <= len(note) <= 500:
            raise ValueError("invalid_review_contract")
        return {**common, "sourceId": source_id, "sourceVersionId": version_id,
                "expectedCommit": commit, "reviewer": reviewer, "decisionNote": note,
                "acceptQuarantineExclusions": payload.get("acceptQuarantineExclusions") is True}

    if path.endswith("/compatibility"):
        name, version, reviewer = payload.get("name"), payload.get("productVersion"), payload.get("reviewer")
        members = payload.get("members")
        if not isinstance(name, str) or not 3 <= len(name) <= 128 or not isinstance(version, str) or not 1 <= len(version) <= 64 or reviewer != "dhslove":
            raise ValueError("invalid_compatibility_contract")
        if not isinstance(members, list) or not 1 <= len(members) <= 16:
            raise ValueError("invalid_compatibility_members")
        safe_members = []
        for member in members:
            version_id = member.get("sourceVersionId") if isinstance(member, dict) else None
            if not isinstance(version_id, str) or not UUID_PATTERN.fullmatch(version_id):
                raise ValueError("invalid_compatibility_members")
            safe_members.append({"sourceVersionId": version_id, "required": member.get("required") is not False})
        return {**common, "name": name, "productVersion": version, "reviewer": reviewer, "members": safe_members}

    if path.endswith("/withdraw"):
        source_id, reviewer, reason = payload.get("sourceId"), payload.get("reviewer"), payload.get("reason")
        if not isinstance(source_id, str) or not UUID_PATTERN.fullmatch(source_id) or reviewer != "dhslove" or not isinstance(reason, str) or not 10 <= len(reason) <= 500:
            raise ValueError("invalid_withdrawal_contract")
        return {**common, "sourceId": source_id, "reviewer": reviewer, "reason": reason}

    if path.endswith("/evaluation"):
        name = payload.get("name")
        profiles = payload.get("sourceProfileIds")
        if profiles is None and payload.get("sourceProfileId") is not None:
            profiles = [payload.get("sourceProfileId")]
        allowed = set(SOURCE_PROFILE_BY_REPOSITORY_BRANCH.values())
        if (
            not isinstance(name, str) or not 3 <= len(name) <= 128
            or not isinstance(profiles, list) or not 1 <= len(profiles) <= 9
            or len(profiles) != len(set(profiles)) or any(profile not in allowed for profile in profiles)
        ):
            raise ValueError("invalid_evaluation_contract")
        return {**common, "name": name, "sourceProfileIds": profiles, "requestedBy": "activepieces"}

    raise ValueError("unsupported_rag_route")


def synology_form_payload(text: str) -> bytes:
    payload = json.dumps({"text": text}, ensure_ascii=False, separators=(",", ":"))
    return urllib.parse.urlencode({"payload": payload}).encode("utf-8")


def classify_chat_response(status: int, body: bytes) -> tuple[str, str]:
    if not 200 <= status < 300:
        return "failed", "http_error"
    try:
        parsed = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return "failed", "invalid_response"
    if parsed.get("success") is True:
        return "succeeded", ""
    error = parsed.get("error") or {}
    code = clean_text(error.get("code"), 32)
    return "failed", code or "application_error"


class GatewayHandler(BaseHTTPRequestHandler):
    server_version = "TechFlowEventGateway"
    sys_version = ""

    @property
    def config(self) -> Config:
        return self.server.config

    @property
    def redis(self) -> RedisClient:
        return self.server.redis

    def log_message(self, _format: str, *_args) -> None:
        return

    def log_event(self, level: str, message: str, **fields) -> None:
        record = {
            "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "level": level,
            "message": message,
            **fields,
        }
        print(json.dumps(record, separators=(",", ":")), flush=True)

    def send_json(self, status: HTTPStatus, payload: dict) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def read_body(self, limit: int) -> bytes | None:
        content_length = self.headers.get("Content-Length")
        if not content_length or not content_length.isdigit():
            self.send_json(
                HTTPStatus.LENGTH_REQUIRED, {"error": "content_length_required"}
            )
            return None
        length = int(content_length)
        if length > limit:
            self.send_json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "too_large"})
            return None
        return self.rfile.read(length)

    @staticmethod
    def post_upstream(url: str, body: bytes, headers: dict[str, str]) -> None:
        request = urllib.request.Request(url, data=body, method="POST", headers=headers)
        with urllib.request.urlopen(request, timeout=10) as response:
            if not 200 <= response.status < 300:
                raise urllib.error.HTTPError(
                    url, response.status, "upstream_rejected", response.headers, None
                )

    def do_GET(self) -> None:
        if self.path not in ("/healthz", "/techflow/hooks/healthz"):
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return
        try:
            healthy = self.redis.ping()
        except RedisError:
            healthy = False
        status = HTTPStatus.OK if healthy else HTTPStatus.SERVICE_UNAVAILABLE
        self.send_json(status, {"status": "ok" if healthy else "unavailable"})

    def do_POST(self) -> None:
        if self.path == self.config.github_path:
            self.handle_github_webhook()
            return
        if self.path == self.config.chat_internal_path:
            self.handle_chat_delivery()
            return
        if self.path.startswith(self.config.path_prefix):
            self.handle_techflow_webhook()
            return
        self.send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def handle_github_webhook(self) -> None:
        request_id = str(uuid.uuid4())
        event_id = self.headers.get("X-GitHub-Delivery", "")
        event_name = self.headers.get("X-GitHub-Event", "")
        signature = self.headers.get("X-Hub-Signature-256", "")
        content_type = self.headers.get("Content-Type", "").lower()
        if not self.config.github_secret:
            self.send_json(
                HTTPStatus.SERVICE_UNAVAILABLE, {"error": "integration_unconfigured"}
            )
            return
        if (
            not EVENT_ID_PATTERN.fullmatch(event_id)
            or event_name not in ("ping", "push", "pull_request")
            or "application/json" not in content_type
        ):
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_request"})
            return
        body = self.read_body(self.config.body_limit)
        if body is None:
            return
        if not github_signature_is_valid(self.config.github_secret, body, signature):
            self.log_event(
                "warning",
                "github_webhook_rejected",
                requestId=request_id,
                eventId=event_id,
                reason="signature_invalid",
            )
            self.send_json(HTTPStatus.UNAUTHORIZED, {"error": "invalid_signature"})
            return
        if event_name == "ping":
            self.log_event(
                "info", "github_webhook_ping", requestId=request_id, eventId=event_id
            )
            self.send_json(HTTPStatus.OK, {"status": "pong"})
            return
        try:
            payload = json.loads(body.decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("payload_not_object")
            normalized = normalize_github_event(
                event_name,
                payload,
                event_id,
                self.config.github_organization,
                time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            )
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            self.log_event(
                "warning",
                "github_webhook_rejected",
                requestId=request_id,
                eventId=event_id,
                reason=clean_text(exc, 64),
            )
            self.send_json(HTTPStatus.UNPROCESSABLE_ENTITY, {"error": "invalid_event"})
            return
        try:
            reserved = self.redis.reserve(
                event_id, self.config.github_event_ttl, namespace="github"
            )
        except RedisError:
            self.send_json(
                HTTPStatus.SERVICE_UNAVAILABLE,
                {"error": "deduplication_unavailable"},
            )
            return
        if not reserved:
            self.log_event(
                "info",
                "github_webhook_duplicate",
                requestId=request_id,
                eventId=event_id,
            )
            self.send_json(HTTPStatus.OK, {"status": "duplicate"})
            return
        if normalized is None:
            self.log_event(
                "info",
                "github_webhook_ignored",
                requestId=request_id,
                eventId=event_id,
            )
            self.send_json(HTTPStatus.OK, {"status": "ignored"})
            return
        if not self.config.github_upstream_url:
            self.redis.release(event_id, namespace="github")
            self.send_json(
                HTTPStatus.SERVICE_UNAVAILABLE, {"error": "upstream_unconfigured"}
            )
            return
        upstream_body = json.dumps(
            normalized, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")
        upstream_headers = {
                "Content-Type": "application/json",
                "X-TechFlow-Event-Id": event_id,
                "X-TechFlow-Request-Id": request_id,
                "X-TechFlow-Verified": "github-v1",
            }
        try:
            self.post_upstream(self.config.github_upstream_url, upstream_body, upstream_headers)
            discovery = normalize_source_discovery_event(normalized, request_id)
            if discovery is not None and self.config.github_source_upstream_url:
                discovery_body = json.dumps(
                    discovery, ensure_ascii=False, separators=(",", ":")
                ).encode("utf-8")
                self.post_upstream(
                    self.config.github_source_upstream_url, discovery_body, upstream_headers
                )
        except (urllib.error.URLError, TimeoutError, OSError):
            try:
                self.redis.release(event_id, namespace="github")
            except RedisError:
                pass
            self.log_event(
                "error",
                "github_webhook_delivery_failed",
                requestId=request_id,
                eventId=event_id,
            )
            self.send_json(HTTPStatus.BAD_GATEWAY, {"error": "upstream_failed"})
            return
        self.log_event(
            "info",
            "github_webhook_accepted",
            requestId=request_id,
            eventId=event_id,
            eventType=normalized["eventType"],
            sourceProfileId=(discovery or {}).get("sourceProfileId"),
        )
        self.send_json(
            HTTPStatus.ACCEPTED,
            {
                "status": "accepted",
                "requestId": request_id,
                "eventId": event_id,
                "sourceDiscovery": discovery is not None,
            },
        )

    def handle_chat_delivery(self) -> None:
        request_id = str(uuid.uuid4())
        if not self.config.chat_webhook_url:
            self.send_json(
                HTTPStatus.SERVICE_UNAVAILABLE, {"error": "integration_unconfigured"}
            )
            return
        body = self.read_body(32768)
        if body is None:
            return
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_json"})
            return
        event_id = clean_text(payload.get("eventId"), 128)
        url = github_url(payload.get("url"), self.config.github_organization)
        text = clean_text(payload.get("text"), 4001)
        if (
            not EVENT_ID_PATTERN.fullmatch(event_id)
            or not url
            or not text
            or len(text) > 4000
        ):
            self.send_json(HTTPStatus.UNPROCESSABLE_ENTITY, {"error": "invalid_message"})
            return
        request = urllib.request.Request(
            self.config.chat_webhook_url,
            data=synology_form_payload(text),
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        slot_name = "synology-chat"
        slot_lease_ms = (self.config.chat_timeout + 5) * 1000
        slot_deadline = time.monotonic() + self.config.chat_timeout + 5
        try:
            while not self.redis.reserve_milliseconds(
                slot_name, slot_lease_ms, "chat-delivery-slot"
            ):
                if time.monotonic() >= slot_deadline:
                    self.log_event(
                        "error",
                        "chat_delivery_failed",
                        requestId=request_id,
                        eventId=event_id,
                        reason="delivery_slot_timeout",
                    )
                    self.send_json(
                        HTTPStatus.SERVICE_UNAVAILABLE,
                        {"error": "chat_busy"},
                    )
                    return
                time.sleep(0.05)
        except RedisError:
            self.send_json(HTTPStatus.SERVICE_UNAVAILABLE, {"error": "dedup_unavailable"})
            return
        try:
            with urllib.request.urlopen(request, timeout=self.config.chat_timeout) as response:
                status = response.status
                response_body = response.read(65536)
        except urllib.error.HTTPError as exc:
            status = exc.code
            response_body = exc.read(65536)
        except (urllib.error.URLError, TimeoutError, OSError):
            self.log_event(
                "error",
                "chat_delivery_unknown",
                requestId=request_id,
                eventId=event_id,
                reason="transport_unknown",
            )
            self.send_json(HTTPStatus.GATEWAY_TIMEOUT, {"error": "delivery_unknown"})
            return
        finally:
            time.sleep(self.config.chat_min_interval_ms / 1000)
            try:
                self.redis.release(slot_name, "chat-delivery-slot")
            except RedisError:
                self.log_event(
                    "error",
                    "chat_delivery_slot_release_failed",
                    requestId=request_id,
                    eventId=event_id,
                    reason="redis_unavailable",
                )
        result, code = classify_chat_response(status, response_body)
        if result != "succeeded":
            self.log_event(
                "error",
                "chat_delivery_failed",
                requestId=request_id,
                eventId=event_id,
                reason=code,
            )
            self.send_json(
                HTTPStatus.UNPROCESSABLE_ENTITY
                if 200 <= status < 300
                else HTTPStatus.BAD_GATEWAY,
                {"error": "chat_rejected", "code": code},
            )
            return
        self.log_event(
            "info",
            "chat_delivery_succeeded",
            requestId=request_id,
            eventId=event_id,
        )
        self.send_json(HTTPStatus.OK, {"success": True, "eventId": event_id})

    def handle_techflow_webhook(self) -> None:
        request_id = str(uuid.uuid4())
        event_id = self.headers.get("X-TechFlow-Event-Id", "")
        body = self.read_body(self.config.body_limit)
        if body is None:
            return
        timestamp = self.headers.get("X-TechFlow-Timestamp", "")
        signature = self.headers.get("X-TechFlow-Signature", "")
        upstream_url = self.config.rag_paths.get(self.path)
        if upstream_url is None:
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "route_not_found"})
            return
        if not upstream_url:
            self.send_json(
                HTTPStatus.SERVICE_UNAVAILABLE, {"error": "integration_unconfigured"}
            )
            return
        if not timestamp or not event_id or not signature:
            self.send_json(
                HTTPStatus.BAD_REQUEST, {"error": "required_header_missing"}
            )
            return
        if not timestamp.isdigit() or not EVENT_ID_PATTERN.fullmatch(event_id):
            self.send_json(
                HTTPStatus.BAD_REQUEST, {"error": "invalid_header_format"}
            )
            return
        now = int(time.time())
        if abs(now - int(timestamp)) > self.config.max_skew:
            self.log_event(
                "warning",
                "webhook_rejected",
                requestId=request_id,
                eventId=event_id,
                reason="timestamp_outside_window",
            )
            self.send_json(HTTPStatus.UNAUTHORIZED, {"error": "stale_request"})
            return
        if not signature_is_valid(self.config.secrets, timestamp, body, signature):
            self.log_event(
                "warning",
                "webhook_rejected",
                requestId=request_id,
                eventId=event_id,
                reason="signature_invalid",
            )
            self.send_json(HTTPStatus.UNAUTHORIZED, {"error": "invalid_signature"})
            return
        try:
            payload = json.loads(body.decode("utf-8"))
            minimized = normalize_rag_event(self.path, payload, event_id, request_id)
            body = json.dumps(minimized, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            self.log_event(
                "warning", "webhook_rejected", requestId=request_id,
                eventId=event_id, reason=str(exc),
            )
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_event_contract"})
            return
        try:
            reserved = self.redis.reserve(
                event_id, self.config.event_ttl, namespace=f"signed:{self.path}"
            )
        except RedisError:
            self.send_json(
                HTTPStatus.SERVICE_UNAVAILABLE,
                {"error": "deduplication_unavailable"},
            )
            return
        if not reserved:
            self.send_json(HTTPStatus.CONFLICT, {"error": "duplicate_event"})
            return
        try:
            self.post_upstream(
                upstream_url,
                body,
                {
                    "Content-Type": "application/json",
                    "X-TechFlow-Event-Id": event_id,
                    "X-TechFlow-Request-Id": request_id,
                    "X-TechFlow-Verified": "true",
                },
            )
        except (urllib.error.URLError, TimeoutError, OSError):
            try:
                self.redis.release(event_id, namespace=f"signed:{self.path}")
            except RedisError:
                pass
            self.send_json(HTTPStatus.BAD_GATEWAY, {"error": "upstream_failed"})
            return
        self.log_event(
            "info", "webhook_accepted", requestId=request_id, eventId=event_id
        )
        self.send_json(
            HTTPStatus.ACCEPTED,
            {"status": "accepted", "requestId": request_id, "eventId": event_id},
        )


class GatewayServer(ThreadingHTTPServer):
    def __init__(self, config: Config) -> None:
        self.config = config
        self.redis = RedisClient(config)
        super().__init__((config.listen_host, config.listen_port), GatewayHandler)


def main() -> int:
    try:
        config = Config()
        server = GatewayServer(config)
    except (RuntimeError, ValueError) as exc:
        print(
            json.dumps(
                {"level": "error", "message": "startup_failed", "reason": str(exc)}
            ),
            file=sys.stderr,
        )
        return 1

    print(
        json.dumps(
            {
                "level": "info",
                "message": "gateway_started",
                "listenPort": config.listen_port,
                "pathPrefix": config.path_prefix,
                "githubPath": config.github_path,
            }
        ),
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
