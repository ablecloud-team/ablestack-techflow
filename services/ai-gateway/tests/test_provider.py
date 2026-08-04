from __future__ import annotations

import unittest

from app.provider import (
    ContextChunk,
    MockEmbeddingsAdapter,
    MockResponsesAdapter,
    PROVIDER_PROFILES,
    ProviderContractError,
    ResponsesRequest,
)


def chunk(index: int = 1, classification: str = "D0", size: int = 20) -> ContextChunk:
    return ContextChunk(
        chunk_id=f"chunk-{index}",
        classification=classification,
        repository="ablecloud-team/ablestack-cloud",
        branch="main",
        commit="a" * 40,
        path="server/src/Main.java",
        text="x" * size,
    )


class ProviderContractTest(unittest.TestCase):
    def test_three_approved_profiles(self) -> None:
        self.assertEqual(
            {"OPENAI_RAG_DEFAULT_V1", "OPENAI_RAG_ESCALATION_V1", "OPENAI_EMBEDDING_V1"},
            set(PROVIDER_PROFILES),
        )

    def test_default_and_escalation_models(self) -> None:
        self.assertEqual("gpt-5.6-terra", PROVIDER_PROFILES["OPENAI_RAG_DEFAULT_V1"].model)
        self.assertEqual("gpt-5.6-sol", PROVIDER_PROFILES["OPENAI_RAG_ESCALATION_V1"].model)

    def test_mock_response_is_structured_and_deterministic(self) -> None:
        request = ResponsesRequest("query-1", "question", "OPENAI_RAG_DEFAULT_V1", (chunk(),))
        first = MockResponsesAdapter().generate(request)
        second = MockResponsesAdapter().generate(request)
        self.assertEqual(first, second)
        self.assertEqual(("chunk-1",), first.citations_used)

    def test_tool_request_is_rejected(self) -> None:
        request = ResponsesRequest("query-1", "question", "OPENAI_RAG_DEFAULT_V1", (chunk(),), tools=("web",))
        with self.assertRaises(ProviderContractError):
            MockResponsesAdapter().generate(request)

    def test_store_request_is_rejected(self) -> None:
        request = ResponsesRequest("query-1", "question", "OPENAI_RAG_DEFAULT_V1", (chunk(),), store=True)
        with self.assertRaises(ProviderContractError):
            MockResponsesAdapter().generate(request)

    def test_more_than_ten_chunks_are_rejected(self) -> None:
        request = ResponsesRequest(
            "query-1", "question", "OPENAI_RAG_DEFAULT_V1", tuple(chunk(index) for index in range(11))
        )
        with self.assertRaises(ProviderContractError):
            MockResponsesAdapter().generate(request)

    def test_non_d0_chunk_is_rejected(self) -> None:
        request = ResponsesRequest("query-1", "question", "OPENAI_RAG_DEFAULT_V1", (chunk(classification="D1"),))
        with self.assertRaises(ProviderContractError):
            MockResponsesAdapter().generate(request)

    def test_embedding_dimension_and_determinism(self) -> None:
        adapter = MockEmbeddingsAdapter()
        first = adapter.embed(["ABLESTACK"])[0]
        second = adapter.embed(["ABLESTACK"])[0]
        self.assertEqual(3072, len(first))
        self.assertEqual(first, second)

    def test_invalid_embedding_profile_is_rejected(self) -> None:
        with self.assertRaises(ProviderContractError):
            MockEmbeddingsAdapter().embed(["ABLESTACK"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
