#!/usr/bin/env python3

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


MODULE_PATH = Path(__file__).with_name("protected_service_guard.py")
SPEC = importlib.util.spec_from_file_location("protected_service_guard", MODULE_PATH)
assert SPEC and SPEC.loader
guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guard)


class ProtectedServiceGuardTests(unittest.TestCase):
    def fixture(self, directory: str):
        root = Path(directory)
        (root / "flows").mkdir()
        flow = {
            "logicalId": "github-chat-v1",
            "action": {"url": "http://chat-adapter:8081/internal/chat/github"},
            "runtime": {"flowId": "flow-1", "publishedVersionId": "version-1"},
        }
        manifest = root / "flows" / "github-chat-v1.json"
        manifest.write_text(json.dumps(flow), encoding="utf-8")
        lock = {
            "services": {
                "github-chat-v1": {
                    "state": "FROZEN",
                    "changePolicy": "PRODUCT_OWNER_EXPLICIT_APPROVAL_ONLY",
                    "flowManifest": "flows/github-chat-v1.json",
                    "flowManifestSha256": guard.sha256(manifest),
                    "flowId": "flow-1",
                    "publishedVersionId": "version-1",
                    "chatAdapterHost": "chat-adapter",
                    "chatAdapterIpv4": "172.30.19.10",
                    "requiredSsrfAllowList": ["172.30.19.10/32"],
                }
            }
        }
        lock_path = root / "protected-services.json"
        lock_path.write_text(json.dumps(lock), encoding="utf-8")
        env = root / ".env"
        env.write_text("AP_SSRF_ALLOW_LIST=172.30.19.3/32,172.30.19.9/32,172.30.19.10/32\n", encoding="utf-8")
        compose = root / "compose.yml"
        compose.write_text("ipv4_address: 172.30.19.10\naliases:\n  - chat-adapter\n", encoding="utf-8")
        ingress = root / "Caddyfile"
        ingress.write_text("path /techflow/hooks/*\nreverse_proxy event-gateway:8081\n", encoding="utf-8")
        return lock_path, env, compose, ingress, manifest

    def test_valid_protected_service(self):
        with tempfile.TemporaryDirectory() as directory:
            guard.validate(*self.fixture(directory)[:4])

    def test_missing_chat_adapter_allowlist_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            lock, env, compose, ingress, _ = self.fixture(directory)
            env.write_text("AP_SSRF_ALLOW_LIST=172.30.19.3/32,172.30.19.9/32\n", encoding="utf-8")
            with self.assertRaises(guard.GuardError):
                guard.validate(lock, env, compose, ingress)

    def test_flow_manifest_change_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            lock, env, compose, ingress, manifest = self.fixture(directory)
            manifest.write_text("{}", encoding="utf-8")
            with self.assertRaises(guard.GuardError):
                guard.validate(lock, env, compose, ingress)


if __name__ == "__main__":
    unittest.main()
