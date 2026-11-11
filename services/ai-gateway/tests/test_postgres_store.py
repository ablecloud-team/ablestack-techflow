from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import unittest
from unittest.mock import MagicMock
from uuid import uuid4

from app.postgres_store import PostgresStore


class PostgresPayloadTest(unittest.TestCase):
    def test_late_kb_revision_metadata_persists_and_clears_only_after_selection(self):
        now = datetime.now(timezone.utc)
        revision = {'postId': '559', 'fingerprint': 'a' * 64, 'authorUserId': '101', 'postNumber': 8}
        row = dict.fromkeys(('discussion_url', 'title', 'draft_answer', 'answer_state', 'reviewer',
                             'published_post_id', 'published_post_url', 'approval_version'))
        row.update(id=uuid4(), discussion_id='199', state='PUBLISHED', draft_version=1, citations=[],
                   source_metadata={'evidenceLedger': {'retained': True}, 'knowledgeBaseRefresh': revision},
                   correlation_id='test', created_at=now, updated_at=now, conversation_state='RESOLVED',
                   resolved_post_id='548', knowledge_base_post_id='550', knowledge_base_version=1)
        connection = MagicMock()
        calls = []
        def execute(sql, params=()):
            sql = sql.strip()
            self.assertEqual(sql.count('%s'), len(params), sql)
            calls.append((sql, params))
            cursor = MagicMock()
            if sql.startswith('SELECT 1') or 'idempotency_key=' in sql:
                cursor.fetchone.return_value = None
            elif sql.startswith('UPDATE community_case'):
                row['source_metadata'] = json.loads(params[-2])
                cursor.fetchone.return_value = dict(row)
            elif sql.startswith('SELECT * FROM community_case'):
                cursor.fetchone.return_value = dict(row)
            elif sql.startswith('INSERT INTO community_turn'):
                cursor.fetchone.return_value = None  # edited/already ingested human source
            return cursor
        connection.execute.side_effect = execute
        store = PostgresStore.__new__(PostgresStore)
        store._pool = MagicMock()
        store._pool.connection.return_value.__enter__.return_value = connection
        result = store.record_community_turn({'discussionId': '199', 'postId': '559', 'postNumber': 8,
            'postAuthorId': '101', 'turnRole': 'STAFF', 'question': '새 해결 보고',
            'knowledgeBaseRefresh': revision, 'preserveResolution': True}, 'turn', 'test')
        self.assertEqual(revision, result['knowledgeBaseRefresh'])
        result = store.mark_community_knowledge_published(row['id'], '최신 KB',
            {'postId': '550', 'postUrl': 'https://forum/d/199/7'}, 'publish', revision_source=revision)
        self.assertEqual(revision, result['knowledgeBaseRevision'])
        self.assertEqual(revision, result['knowledgeBaseRefresh'])
        result = store.mark_community_knowledge_solution_selected(row['id'],
            {'postId': '550', 'selectedByUserId': '1'}, 'select')
        self.assertIsNone(result['knowledgeBaseRefresh'])
        self.assertEqual({'retained': True}, result['evidenceLedger'])
        row['source_metadata']['knowledgeBaseRefresh'] = revision
        self.assertIsNotNone(store.cancel_community_knowledge_refresh(row['id'], '560', 'cancel')['knowledgeBaseRefresh'])
        self.assertIsNone(store.cancel_community_knowledge_refresh(row['id'], '559', 'cancel')['knowledgeBaseRefresh'])
        self.assertTrue(any('UPDATE community_turn SET content=' in sql for sql, _ in calls))

    def test_returning_star_job_id_is_mapped(self) -> None:
        job_id = uuid4()
        source_id = uuid4()
        version_id = uuid4()
        now = datetime.now(timezone.utc)
        payload = PostgresStore._job_payload(
            {
                "id": job_id,
                "job_type": "INGESTION",
                "source_id": source_id,
                "source_version_id": version_id,
                "state": "PENDING",
                "failure_class": None,
                "error_code": None,
                "requested_by": "canary",
                "created_at": now,
                "updated_at": now,
            }
        )
        self.assertEqual(job_id, payload["jobId"])

    def test_aliased_job_id_is_also_supported(self) -> None:
        job_id = uuid4()
        now = datetime.now(timezone.utc)
        payload = PostgresStore._job_payload(
            {
                "job_id": job_id,
                "job_type": "DELETION",
                "source_id": uuid4(),
                "source_version_id": uuid4(),
                "state": "PENDING",
                "failure_class": None,
                "error_code": None,
                "requested_by": "system",
                "created_at": now,
                "updated_at": now,
            }
        )
        self.assertEqual(job_id, payload["jobId"])

    def test_registry_query_excludes_legacy_canary_profiles(self) -> None:
        implementation = (Path(__file__).resolve().parents[1] / "app" / "postgres_store.py").read_text(encoding="utf-8")
        self.assertIn("WHERE source_profile_id = ANY(%s)", implementation)

    def test_indexing_query_maps_database_name_to_contract_alias(self) -> None:
        implementation = (Path(__file__).resolve().parents[1] / "app" / "postgres_store.py").read_text(encoding="utf-8")
        self.assertIn('f.source_kind AS "sourceKind"', implementation)
        self.assertIn("Jsonb(metrics)", implementation)


if __name__ == "__main__":
    unittest.main()
