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

    def test_postgres_requires_dsn(self) -> None:
        with self.assertRaises(ConfigurationError):
            Settings(store_backend="postgres").validate()

    def test_issue_41_rejects_real_provider(self) -> None:
        with self.assertRaises(ConfigurationError):
            Settings(provider_mode="openai").validate()

    def test_openai_mode_accepts_runtime_secret_file_reference(self) -> None:
        Settings(provider_mode="openai", openai_api_key_file="/run/secrets/openai_api_key").validate()

    def test_only_d0_is_allowed(self) -> None:
        with self.assertRaises(ConfigurationError):
            Settings(classification="D1").validate()

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
