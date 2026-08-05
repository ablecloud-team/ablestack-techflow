"""Pure indexing composition and Hybrid Retrieval ranking helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Sequence
from uuid import UUID

from .chunking import ChunkRecord, RelationRecord, SymbolRecord, chunk_file
from .embedding import EmbeddingBatchResult, EmbeddingsAdapter, MAX_BATCH_ITEMS


@dataclass(frozen=True)
class ProviderAudit:
    provider: str
    requested_model: str
    returned_model: str
    input_tokens: int
    request_id: str
    latency_ms: int


@dataclass(frozen=True)
class IndexBundle:
    indexed_file_count: int
    chunks: tuple[ChunkRecord, ...]
    symbols: tuple[SymbolRecord, ...]
    relations: tuple[RelationRecord, ...]
    embeddings: tuple[tuple[UUID, tuple[float, ...]], ...]
    provider_audits: tuple[ProviderAudit, ...]
    parsed_file_count: int
    fallback_file_count: int


def build_index_bundle(
    source_version_id: UUID,
    files: Sequence[dict[str, Any]],
    adapter: EmbeddingsAdapter,
    batch_size: int = 64,
) -> IndexBundle:
    if not 1 <= batch_size <= MAX_BATCH_ITEMS:
        raise ValueError("embedding batch size must be between 1 and 128")
    chunks: list[ChunkRecord] = []
    symbols: list[SymbolRecord] = []
    relations: list[RelationRecord] = []
    parsed_files = 0
    fallback_files = 0
    for item in sorted(files, key=lambda row: row["path"]):
        parsed = chunk_file(source_version_id, item["sourceKind"], item["path"], item["content"])
        chunks.extend(parsed.chunks)
        symbols.extend(parsed.symbols)
        relations.extend(parsed.relations)
        if parsed.parser_status == "PARSED":
            parsed_files += 1
        else:
            fallback_files += 1
    embeddings: list[tuple[UUID, tuple[float, ...]]] = []
    audits: list[ProviderAudit] = []
    for offset in range(0, len(chunks), batch_size):
        batch = chunks[offset : offset + batch_size]
        result: EmbeddingBatchResult = adapter.embed([chunk.content for chunk in batch])
        embeddings.extend((chunk.id, vector) for chunk, vector in zip(batch, result.vectors, strict=True))
        audits.append(
            ProviderAudit(
                provider=result.provider,
                requested_model=result.requested_model,
                returned_model=result.returned_model,
                input_tokens=result.input_tokens,
                request_id=result.request_id,
                latency_ms=result.latency_ms,
            )
        )
    return IndexBundle(
        indexed_file_count=len(files),
        chunks=tuple(chunks),
        symbols=tuple(symbols),
        relations=tuple(relations),
        embeddings=tuple(embeddings),
        provider_audits=tuple(audits),
        parsed_file_count=parsed_files,
        fallback_file_count=fallback_files,
    )


def reciprocal_rank_fusion(
    rankings: dict[str, Sequence[UUID]],
    source_kinds: dict[UUID, str],
    k: int = 60,
) -> list[tuple[UUID, float, tuple[str, ...]]]:
    """Fuse FTS, identifier, and vector ranks with the approved test-evidence weight."""

    scores: dict[UUID, float] = {}
    channels: dict[UUID, set[str]] = {}
    for channel, candidates in rankings.items():
        for rank, chunk_id in enumerate(candidates, start=1):
            weight = 0.6 if source_kinds.get(chunk_id) == "TEST_CODE" else 1.0
            scores[chunk_id] = scores.get(chunk_id, 0.0) + weight / (k + rank)
            channels.setdefault(chunk_id, set()).add(channel)
    return sorted(
        ((chunk_id, score, tuple(sorted(channels[chunk_id]))) for chunk_id, score in scores.items()),
        key=lambda item: (-item[1], str(item[0])),
    )


def cosine_similarity(left: Iterable[float], right: Iterable[float]) -> float:
    left_values, right_values = tuple(left), tuple(right)
    if len(left_values) != len(right_values) or not left_values:
        return 0.0
    numerator = sum(a * b for a, b in zip(left_values, right_values, strict=True))
    left_norm = sum(value * value for value in left_values) ** 0.5
    right_norm = sum(value * value for value in right_values) ** 0.5
    return numerator / (left_norm * right_norm) if left_norm and right_norm else 0.0
