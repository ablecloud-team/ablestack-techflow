#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import hmac
import importlib.util
from pathlib import Path
import unittest

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


if __name__ == "__main__":
    unittest.main()
