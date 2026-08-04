"""Runtime configuration with secret-safe validation."""

from __future__ import annotations

from dataclasses import dataclass
import os


class ConfigurationError(RuntimeError):
    """Raised when the runtime boundary is unsafe or incomplete."""


@dataclass(frozen=True, repr=False)
class Settings:
    environment: str = "development"
    store_backend: str = "memory"
    database_dsn: str | None = None
    provider_mode: str = "mock"
    classification: str = "D0"
    log_level: str = "INFO"
    database_pool_min: int = 1
    database_pool_max: int = 4

    @classmethod
    def from_env(cls) -> "Settings":
        settings = cls(
            environment=os.getenv("TECHFLOW_RAG_ENVIRONMENT", "development").strip().lower(),
            store_backend=os.getenv("TECHFLOW_RAG_STORE", "memory").strip().lower(),
            database_dsn=os.getenv("TECHFLOW_RAG_DATABASE_DSN") or None,
            provider_mode=os.getenv("TECHFLOW_RAG_PROVIDER_MODE", "mock").strip().lower(),
            classification=os.getenv("TECHFLOW_RAG_CLASSIFICATION", "D0").strip().upper(),
            log_level=os.getenv("TECHFLOW_RAG_LOG_LEVEL", "INFO").strip().upper(),
            database_pool_min=int(os.getenv("TECHFLOW_RAG_DATABASE_POOL_MIN", "1")),
            database_pool_max=int(os.getenv("TECHFLOW_RAG_DATABASE_POOL_MAX", "4")),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        if self.store_backend not in {"memory", "postgres"}:
            raise ConfigurationError("TECHFLOW_RAG_STORE must be memory or postgres")
        if self.store_backend == "postgres" and not self.database_dsn:
            raise ConfigurationError("TECHFLOW_RAG_DATABASE_DSN is required for postgres")
        if self.provider_mode != "mock":
            raise ConfigurationError("Issue #41 supports mock provider mode only")
        if self.classification != "D0":
            raise ConfigurationError("Issue #41 permits D0 data only")
        if self.database_pool_min < 0 or self.database_pool_max < max(1, self.database_pool_min):
            raise ConfigurationError("invalid database pool bounds")

    def __repr__(self) -> str:
        return (
            "Settings(environment={!r}, store_backend={!r}, database_dsn=<redacted>, "
            "provider_mode={!r}, classification={!r}, log_level={!r}, "
            "database_pool_min={!r}, database_pool_max={!r})"
        ).format(
            self.environment,
            self.store_backend,
            self.provider_mode,
            self.classification,
            self.log_level,
            self.database_pool_min,
            self.database_pool_max,
        )
