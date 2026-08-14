from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from app.config import ConfigurationError, Settings


class SettingsTest(unittest.TestCase):
    def test_safe_defaults(self) -> None:
        settings = Settings()
        settings.validate()
        self.assertEqual("memory", settings.store_backend)
        self.assertEqual("mock", settings.provider_mode)
        self.assertEqual(128, settings.embedding_batch_size)
        self.assertEqual(50 * 1024 * 1024, settings.artifact_max_bytes)
        self.assertEqual(100 * 1024 * 1024, settings.artifact_max_extracted_bytes)

    def test_large_upload_boundary_is_bounded(self) -> None:
        Settings(
            artifact_max_bytes=50 * 1024 * 1024,
            artifact_max_extracted_bytes=100 * 1024 * 1024,
        ).validate()
        with self.assertRaises(ConfigurationError):
            Settings(
                artifact_max_bytes=50 * 1024 * 1024 + 1,
                artifact_max_extracted_bytes=100 * 1024 * 1024,
            ).validate()

    def test_postgres_requires_dsn(self) -> None:
        with self.assertRaises(ConfigurationError):
            Settings(store_backend="postgres").validate()

    def test_issue_41_rejects_real_provider(self) -> None:
        with self.assertRaises(ConfigurationError):
            Settings(provider_mode="openai").validate()

    def test_openai_mode_accepts_runtime_secret_file_reference(self) -> None:
        Settings(
            provider_mode="openai",
            openai_api_key_file="/run/secrets/openai_api_key",
            openai_project_id_file="/run/secrets/openai_project_id",
            safety_identifier_salt_file="/run/secrets/safety_identifier_salt",
        ).validate()

    def test_only_d0_is_allowed(self) -> None:
        with self.assertRaises(ConfigurationError):
            Settings(classification="D1").validate()

    def test_internal_flarum_api_route_keeps_public_https_origin(self) -> None:
        Settings(
            flarum_base_url="http://172.16.0.234",
            flarum_public_url="https://community.ablecloud.io",
        ).validate()

    def test_unapproved_flarum_routes_are_rejected(self) -> None:
        with self.assertRaises(ConfigurationError):
            Settings(flarum_base_url="http://example.invalid").validate()
        with self.assertRaises(ConfigurationError):
            Settings(flarum_public_url="http://172.16.0.234").validate()

    def test_repr_redacts_dsn(self) -> None:
        value = repr(Settings(database_dsn="postgresql://user:runtime-value@db/name"))
        self.assertNotIn("runtime-value", value)
        self.assertIn("<redacted>", value)

    def test_environment_loading(self) -> None:
        with patch.dict(
            os.environ,
            {
                "TECHFLOW_RAG_STORE": "postgres",
                "TECHFLOW_RAG_DATABASE_DSN": "postgresql://runtime-value",
                "TECHFLOW_RAG_PROVIDER_MODE": "mock",
            },
            clear=True,
        ):
            settings = Settings.from_env()
        self.assertEqual("postgres", settings.store_backend)


if __name__ == "__main__":
    unittest.main()
