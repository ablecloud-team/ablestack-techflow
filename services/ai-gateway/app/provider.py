"""Versioned provider profiles and non-network mock adapters for Issue #41."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Iterable, Sequence


class ProviderContractError(ValueError):
    """Raised before any provider call when the request crosses a policy boundary."""


@dataclass(frozen=True)
class ProviderProfile:
    profile_id: str
    surface: str
    model: str
    reasoning_effort: str | None = None
    embedding_dimension: int | None = None
    version: int = 1


PROVIDER_PROFILES: dict[str, ProviderProfile] = {
    "OPENAI_RAG_DEFAULT_V1": ProviderProfile(
        profile_id="OPENAI_RAG_DEFAULT_V1",
        surface="responses-api",
        model="gpt-5.6-terra",
        reasoning_effort="medium",
    ),
    "OPENAI_RAG_ESCALATION_V1": ProviderProfile(
        profile_id="OPENAI_RAG_ESCALATION_V1",
        surface="responses-api",
        model="gpt-5.6-sol",
        reasoning_effort="high",
    ),
    "OPENAI_EMBEDDING_V1": ProviderProfile(
        profile_id="OPENAI_EMBEDDING_V1",
        surface="embeddings-api",
        model="text-embedding-3-large",
        embedding_dimension=3072,
    ),
}


@dataclass(frozen=True)
class ContextChunk:
    chunk_id: str
    classification: str
    repository: str
    branch: str
    commit: str
    path: str
    text: str


@dataclass(frozen=True)
class ResponsesRequest:
    query_id: str
    question: str
    profile_id: str
    context: tuple[ContextChunk, ...]
    store: bool = False
    background: bool = False
    tools: tuple[str, ...] = ()
    structured_output: bool = True


@dataclass(frozen=True)
class ResponsesResult:
    state: str
    answer: str
    citations_used: tuple[str, ...]
    requested_model_id: str
    returned_model_id: str
    request_id: str
    response_id: str
    input_tokens: int
    output_tokens: int


def validate_responses_request(request: ResponsesRequest) -> ProviderProfile:
    profile = PROVIDER_PROFILES.get(request.profile_id)
    if profile is None or profile.surface != "responses-api":
        raise ProviderContractError("unapproved responses provider profile")
    if request.store or request.background or request.tools:
        raise ProviderContractError("store, background, and tools must be disabled")
    if not request.structured_output:
        raise ProviderContractError("structured output is required")
    if not request.context or len(request.context) > 10:
        raise ProviderContractError("responses context must contain 1 to 10 chunks")
    if any(chunk.classification != "D0" for chunk in request.context):
        raise ProviderContractError("only D0 context is permitted")
    if any(len(chunk.text.encode("utf-8")) > 1_048_576 for chunk in request.context):
        raise ProviderContractError("whole file or oversized context is prohibited")
    return profile


class MockResponsesAdapter:
    """Deterministic adapter that validates the future OpenAI request contract."""

    def generate(self, request: ResponsesRequest) -> ResponsesResult:
        profile = validate_responses_request(request)
        digest = hashlib.sha256(request.query_id.encode("utf-8")).hexdigest()[:16]
        citations = tuple(chunk.chunk_id for chunk in request.context[:2])
        return ResponsesResult(
            state="ANSWERED",
            answer="Mock provider response for contract verification.",
            citations_used=citations,
            requested_model_id=profile.model,
            returned_model_id=profile.model,
            request_id=f"mock-request-{digest}",
            response_id=f"mock-response-{digest}",
            input_tokens=sum(max(1, len(chunk.text) // 4) for chunk in request.context),
            output_tokens=12,
        )


class MockEmbeddingsAdapter:
    """Returns deterministic fixed-size vectors without network access."""

    def embed(self, texts: Iterable[str], profile_id: str = "OPENAI_EMBEDDING_V1") -> list[list[float]]:
        profile = PROVIDER_PROFILES.get(profile_id)
        if profile is None or profile.surface != "embeddings-api" or not profile.embedding_dimension:
            raise ProviderContractError("unapproved embedding provider profile")
        values = list(texts)
        if not values or len(values) > 128:
            raise ProviderContractError("embedding batch must contain 1 to 128 items")
        vectors: list[list[float]] = []
        for value in values:
            if not value or len(value.encode("utf-8")) > 1_048_576:
                raise ProviderContractError("invalid embedding input")
            seed = hashlib.sha256(value.encode("utf-8")).digest()
            vectors.append([
                (seed[index % len(seed)] - 127.5) / 127.5
                for index in range(profile.embedding_dimension)
            ])
        return vectors


def profile_payloads(profiles: Sequence[ProviderProfile] | None = None) -> list[dict[str, object]]:
    selected = profiles or tuple(PROVIDER_PROFILES.values())
    return [
        {
            "profileId": profile.profile_id,
            "surface": profile.surface,
            "model": profile.model,
            "reasoningEffort": profile.reasoning_effort,
            "embeddingDimension": profile.embedding_dimension,
            "version": profile.version,
        }
        for profile in selected
    ]
