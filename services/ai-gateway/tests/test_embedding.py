from __future__ import annotations

from types import SimpleNamespace
import unittest

from app.embedding import MAX_BATCH_BYTES, MAX_INPUT_BYTES, MockEmbeddingsAdapter, OpenAIEmbeddingsAdapter, validate_inputs
from app.provider import ProviderContractError


class FakeEmbeddings:
    def create(self, **kwargs):
        self.kwargs = kwargs
        vector = [0.0] * 3072
        return SimpleNamespace(
            data=[SimpleNamespace(index=0, embedding=vector)], model="text-embedding-3-large",
            usage=SimpleNamespace(prompt_tokens=3), _request_id="request-43",
        )


class EmbeddingTest(unittest.TestCase):
    def test_mock_is_normalized_and_deterministic(self) -> None:
        adapter = MockEmbeddingsAdapter()
        first = adapter.embed(["ABLESTACK"])
        second = adapter.embed(["ABLESTACK"])
        self.assertEqual(first.vectors, second.vectors)
        self.assertEqual(3072, len(first.vectors[0]))
        self.assertAlmostEqual(1.0, sum(value * value for value in first.vectors[0]) ** 0.5, places=6)

    def test_empty_and_oversized_inputs_are_rejected(self) -> None:
        with self.assertRaises(ProviderContractError):
            validate_inputs([])
        with self.assertRaises(ProviderContractError):
            validate_inputs(["x" * (MAX_INPUT_BYTES + 1)])
        with self.assertRaises(ProviderContractError):
            validate_inputs(["x" * (MAX_BATCH_BYTES // 64 + 1)] * 64)

    def test_official_sdk_contract_sets_model_dimension_and_no_storage(self) -> None:
        fake = FakeEmbeddings()
        adapter = OpenAIEmbeddingsAdapter("unused", client=SimpleNamespace(embeddings=fake))
        result = adapter.embed(["hello"])
        self.assertEqual("text-embedding-3-large", fake.kwargs["model"])
        self.assertEqual(3072, fake.kwargs["dimensions"])
        self.assertEqual("float", fake.kwargs["encoding_format"])
        self.assertNotIn("store", fake.kwargs)
        self.assertEqual("request-43", result.request_id)


if __name__ == "__main__":
    unittest.main()
