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
        upstream_request = urllib.request.Request(
            self.config.github_upstream_url,
            data=upstream_body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "X-TechFlow-Event-Id": event_id,
                "X-TechFlow-Request-Id": request_id,
                "X-TechFlow-Verified": "github-v1",
            },
        )
        try:
            with urllib.request.urlopen(upstream_request, timeout=10) as response:
                if not 200 <= response.status < 300:
                    raise urllib.error.HTTPError(
                        self.config.github_upstream_url,
                        response.status,
                        "upstream_rejected",
                        response.headers,
                        None,
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
        )
        self.send_json(
            HTTPStatus.ACCEPTED,
            {"status": "accepted", "requestId": request_id, "eventId": event_id},
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
            reserved = self.redis.reserve(event_id, self.config.event_ttl)
        except RedisError:
            self.send_json(
                HTTPStatus.SERVICE_UNAVAILABLE,
                {"error": "deduplication_unavailable"},
            )
            return
        if not reserved:
            self.send_json(HTTPStatus.CONFLICT, {"error": "duplicate_event"})
            return
        if self.config.upstream_url:
            upstream_request = urllib.request.Request(
                self.config.upstream_url,
                data=body,
                method="POST",
                headers={
                    "Content-Type": self.headers.get(
                        "Content-Type", "application/octet-stream"
                    ),
                    "X-TechFlow-Event-Id": event_id,
                    "X-TechFlow-Request-Id": request_id,
                    "X-TechFlow-Verified": "true",
                },
            )
            try:
                with urllib.request.urlopen(upstream_request, timeout=10) as response:
                    if not 200 <= response.status < 300:
                        raise urllib.error.HTTPError(
                            self.config.upstream_url,
                            response.status,
                            "upstream_rejected",
                            response.headers,
                            None,
                        )
            except (urllib.error.URLError, TimeoutError, OSError):
                try:
                    self.redis.release(event_id)
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
