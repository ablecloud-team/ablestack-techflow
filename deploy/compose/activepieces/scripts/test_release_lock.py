#!/usr/bin/env python3

import importlib.util
import json
import pathlib
import tempfile
import unittest


MODULE_PATH = pathlib.Path(__file__).with_name("release_lock.py")
SPEC = importlib.util.spec_from_file_location("techflow_release_lock", MODULE_PATH)
assert SPEC and SPEC.loader
release_lock = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release_lock)

DIGESTS = {
    service: f"sha256:{index:064x}"
    for index, service in enumerate(release_lock.SERVICES, start=1)
}


def sample_lock():
    services = {}
    for service in release_lock.SERVICES:
        digest = DIGESTS[service]
        if service == "event-gateway":
            services[service] = {
                "version": "0.1.0",
                "environmentKey": release_lock.ENVIRONMENT_KEYS[service],
                "imageRef": "example/event-gateway:0.1.0",
                "expectedImageId": digest,
                "baseImageRef": f"python:3.12-alpine@{digest}",
            }
        else:
            services[service] = {
                "version": "test",
                "environmentKey": release_lock.ENVIRONMENT_KEYS[service],
                "imageRef": f"example/{service}:1.0@{digest}",
                "registryDigest": digest,
                "expectedImageId": digest,
            }
    services["worker"]["imageRef"] = services["app"]["imageRef"]
    services["worker"]["registryDigest"] = services["app"]["registryDigest"]
    return {
        "schemaVersion": "1.0",
        "releaseId": "test-release",
        "createdAt": "2026-07-31T00:00:00Z",
        "platform": "linux/amd64",
        "services": services,
        "policy": {},
    }


class ReleaseLockTests(unittest.TestCase):
    def write_lock(self, directory, data=None):
        path = pathlib.Path(directory) / "lock.json"
        path.write_text(json.dumps(data or sample_lock()), encoding="utf-8")
        return path

    def test_valid_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            data = release_lock.load_lock(self.write_lock(directory))
        self.assertEqual(data["releaseId"], "test-release")

    def test_mutable_external_ref_is_rejected(self):
        data = sample_lock()
        data["services"]["redis"]["imageRef"] = "redis:7.0.7"
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                release_lock.load_lock(self.write_lock(directory, data))

    def test_digest_mismatch_is_rejected(self):
        data = sample_lock()
        data["services"]["postgres"]["registryDigest"] = DIGESTS["redis"]
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                release_lock.load_lock(self.write_lock(directory, data))

    def test_environment_contains_only_image_keys(self):
        data = sample_lock()
        with tempfile.TemporaryDirectory() as directory:
            output = pathlib.Path(directory) / "release.env"
            release_lock.write_env(data, output)
            text = output.read_text(encoding="utf-8")
        self.assertIn("AP_IMAGE_REF=", text)
        self.assertIn("TECHFLOW_GATEWAY_VERSION=0.1.0", text)
        self.assertNotIn("PASSWORD", text)
        self.assertEqual(text.count("AP_IMAGE_REF="), 1)

    def test_runtime_ref_adds_digest(self):
        ref = release_lock.immutable_runtime_ref(
            "example/app:1.0",
            [f"example/app@{DIGESTS['app']}"],
            DIGESTS["app"],
        )
        self.assertEqual(ref, f"example/app:1.0@{DIGESTS['app']}")

    def test_compare_accepts_identical_runtime_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            first = self.write_lock(directory)
            second = pathlib.Path(directory) / "second.json"
            second.write_text(json.dumps(sample_lock()), encoding="utf-8")
            release_lock.compare(first, second)

    def test_source_matches_lock(self):
        data = sample_lock()
        with tempfile.TemporaryDirectory() as directory:
            compose = pathlib.Path(directory) / "compose.yml"
            dockerfile = pathlib.Path(directory) / "Dockerfile"
            compose.write_text(
                "\n".join(item["imageRef"] for item in data["services"].values()),
                encoding="utf-8",
            )
            dockerfile.write_text(
                f"FROM {data['services']['event-gateway']['baseImageRef']}\n",
                encoding="utf-8",
            )
            release_lock.validate_source(data, compose, dockerfile)


if __name__ == "__main__":
    unittest.main()
