"""Versioned Mock and OpenAI Embeddings adapters for Issue #43."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
from pathlib import Path
import time
from typing import Protocol, Sequence

from .provider import PROVIDER_PROFILES, ProviderContractError, ProviderProfile


MAX_BATCH_ITEMS = 128
MAX_INPUT_BYTES = 24 * 1024
MAX_BATCH_BYTES = 2 * 1024 * 1024


@dataclass(frozen=True)
class EmbeddingBatchResult:
    vectors: tuple[tuple[float, ...], ...]
    provider: str
    requested_model: str
    returned_model: str
    input_tokens: int
    request_id: str
    latency_ms: int


class EmbeddingsAdapter(Protocol):
    profile: ProviderProfile

    def embed(self, texts: Sequence[str]) -> EmbeddingBatchResult: ...


def validate_inputs(texts: Sequence[str]) -> tuple[str, ...]:
    values = tuple(texts)
    if not values or len(values) > MAX_BATCH_ITEMS:
        raise ProviderContractError("embedding batch must contain 1 to 128 items")
    encoded = [value.encode("utf-8") for value in values]
    if any(not value.strip() or len(raw) > MAX_INPUT_BYTES for value, raw in zip(values, encoded, strict=True)):
        raise ProviderContractError("embedding input is empty or exceeds the TechFlow safety limit")
    if sum(map(len, encoded)) > MAX_BATCH_BYTES:
        raise ProviderContractError("embedding batch exceeds the TechFlow safety limit")
    return values


class MockEmbeddingsAdapter:
    """Deterministic normalized vectors without network access."""

    def __init__(self, profile_id: str = "OPENAI_EMBEDDING_V1") -> None:
        profile = PROVIDER_PROFILES.get(profile_id)
        if profile is None or profile.surface != "embeddings-api" or not profile.embedding_dimension:
            raise ProviderContractError("unapproved embedding provider profile")
        self.profile = profile

    def embed(self, texts: Sequence[str]) -> EmbeddingBatchResult:
        values = validate_inputs(texts)
        started = time.perf_counter()
        vectors: list[tuple[float, ...]] = []
        for value in values:
            seed = hashlib.sha256(value.encode("utf-8")).digest()
            raw = [(seed[index % len(seed)] - 127.5) / 127.5 for index in range(self.profile.embedding_dimension or 0)]
            magnitude = math.sqrt(sum(item * item for item in raw)) or 1.0
            vectors.append(tuple(item / magnitude for item in raw))
        digest = hashlib.sha256("\0".join(values).encode("utf-8")).hexdigest()[:20]
        return EmbeddingBatchResult(
            vectors=tuple(vectors),
            provider="mock",
            requested_model=self.profile.model,
            returned_model=self.profile.model,
            input_tokens=sum(max(1, len(value) // 4) for value in values),
            request_id=f"mock-embedding-{digest}",
            latency_ms=max(0, round((time.perf_counter() - started) * 1000)),
        )


class OpenAIEmbeddingsAdapter:
    """Official OpenAI Python SDK adapter. Construction requires a runtime secret file."""

    def __init__(
        self,
        api_key_file: str,
        profile_id: str = "OPENAI_EMBEDDING_V1",
        client: object | None = None,
    ) -> None:
        profile = PROVIDER_PROFILES.get(profile_id)
        if profile is None or profile.surface != "embeddings-api" or not profile.embedding_dimension:
            raise ProviderContractError("unapproved embedding provider profile")
        self.profile = profile
        if client is None:
            path = Path(api_key_file)
            if not path.is_file():
                raise ProviderContractError("OpenAI API key secret file is unavailable")
            key = path.read_text(encoding="utf-8").strip()
            if not key:
                raise ProviderContractError("OpenAI API key secret file is empty")
            from openai import OpenAI

            client = OpenAI(api_key=key, timeout=30.0, max_retries=2)
        self._client = client

    def embed(self, texts: Sequence[str]) -> EmbeddingBatchResult:
        values = validate_inputs(texts)
        started = time.perf_counter()
        response = self._client.embeddings.create(
            input=list(values),
            model=self.profile.model,
            dimensions=self.profile.embedding_dimension,
            encoding_format="float",
        )
        ordered = sorted(response.data, key=lambda item: item.index)
        vectors = tuple(tuple(float(value) for value in item.embedding) for item in ordered)
        if len(vectors) != len(values) or any(len(vector) != self.profile.embedding_dimension for vector in vectors):
            raise ProviderContractError("OpenAI embedding response dimension or count mismatch")
        return EmbeddingBatchResult(
            vectors=vectors,
            provider="openai",
            requested_model=self.profile.model,
            returned_model=str(response.model),
            input_tokens=int(response.usage.prompt_tokens),
            request_id=str(getattr(response, "_request_id", "") or "unavailable"),
            latency_ms=max(0, round((time.perf_counter() - started) * 1000)),
        )


def build_embedding_adapter(settings) -> EmbeddingsAdapter:
    if settings.provider_mode == "mock":
        return MockEmbeddingsAdapter()
    if settings.provider_mode == "openai":
        return OpenAIEmbeddingsAdapter(settings.openai_api_key_file or "")
    raise ProviderContractError("unsupported embedding provider mode")
