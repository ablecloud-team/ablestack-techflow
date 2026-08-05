from __future__ import annotations

import unittest
from uuid import UUID, uuid4

from app.embedding import MockEmbeddingsAdapter
from app.indexing import build_index_bundle, reciprocal_rank_fusion


class IndexingTest(unittest.TestCase):
    def test_bundle_preserves_file_count_and_one_embedding_per_chunk(self) -> None:
        bundle = build_index_bundle(
            uuid4(),
            [{"path": "README.md", "sourceKind": "DOCUMENTATION", "content": "# 제목\n본문"},
             {"path": "config.yml", "sourceKind": "BUILD_SCHEMA", "content": "enabled: true"}],
            MockEmbeddingsAdapter(),
            batch_size=1,
        )
        self.assertEqual(2, bundle.indexed_file_count)
        self.assertEqual(len(bundle.chunks), len(bundle.embeddings))
        self.assertEqual(len(bundle.chunks), len(bundle.provider_audits))

    def test_rrf_is_stable_and_test_evidence_weighted_down(self) -> None:
        code_id = UUID("00000000-0000-0000-0000-000000000001")
        test_id = UUID("00000000-0000-0000-0000-000000000002")
        ranked = reciprocal_rank_fusion(
            {"fts": [test_id, code_id], "vector": [code_id, test_id]},
            {code_id: "SOURCE_CODE", test_id: "TEST_CODE"},
        )
        self.assertEqual(code_id, ranked[0][0])
        self.assertEqual(("fts", "vector"), ranked[0][2])


if __name__ == "__main__":
    unittest.main()
