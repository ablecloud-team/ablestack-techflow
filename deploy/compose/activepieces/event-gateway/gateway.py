#!/usr/bin/env python3
"""Minimal fail-closed signed Webhook ingress for the TechFlow test server."""

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
import urllib.request
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

EVENT_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
SIGNATURE_PATTERN = re.compile(r"^sha256=([0-9a-fA-F]{64})$")


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

    def reserve(self, event_id: str, ttl: int) -> bool:
        key_hash = hashlib.sha256(event_id.encode("utf-8")).hexdigest()
        key = f"techflow:webhook:event:{key_hash}"
        return self._command("SET", key, "1", "NX", "EX", str(ttl)) == "OK"

    def release(self, event_id: str) -> None:
        key_hash = hashlib.sha256(event_id.encode("utf-8")).hexdigest()
        key = f"techflow:webhook:event:{key_hash}"
        self._command("DEL", key)


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
        request_id = str(uuid.uuid4())
        event_id = self.headers.get("X-TechFlow-Event-Id", "")

        if not self.path.startswith(self.config.path_prefix):
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return

        content_length = self.headers.get("Content-Length")
        if not content_length or not content_length.isdigit():
            self.send_json(
                HTTPStatus.LENGTH_REQUIRED, {"error": "content_length_required"}
            )
            return
        length = int(content_length)
        if length > self.config.body_limit:
            self.send_json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "too_large"})
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

        body = self.rfile.read(length)
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
            self.log_event(
                "error",
                "webhook_rejected",
                requestId=request_id,
                eventId=event_id,
                reason="deduplication_unavailable",
            )
            self.send_json(
                HTTPStatus.SERVICE_UNAVAILABLE,
                {"error": "deduplication_unavailable"},
            )
            return
        if not reserved:
            self.log_event(
                "info",
                "webhook_rejected",
                requestId=request_id,
                eventId=event_id,
                reason="duplicate_event",
            )
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
                self.log_event(
                    "error",
                    "webhook_delivery_failed",
                    requestId=request_id,
                    eventId=event_id,
                )
                self.send_json(HTTPStatus.BAD_GATEWAY, {"error": "upstream_failed"})
                return

        self.log_event(
            "info",
            "webhook_accepted",
            requestId=request_id,
            eventId=event_id,
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
