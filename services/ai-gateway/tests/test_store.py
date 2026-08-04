from __future__ import annotations

import unittest
from uuid import UUID, uuid4

from app.store import InvalidStateError, MemoryStore, NotFoundError


SOURCE = {
    "sourceProfileId": "CLOUD_MAIN",
    "repository": "ablecloud-team/ablestack-cloud",
    "branch": "main",
    "commit": "a" * 40,
    "sourceKind": "SOURCE_CODE",
    "classification": "D0",
    "licenseSpdx": "Apache-2.0",
}


class MemoryStoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self.store = MemoryStore()

    def test_create_source_is_idempotent(self) -> None:
        first = self.store.create_source(SOURCE, "create-source-0001")
        second = self.store.create_source({**SOURCE, "branch": "other"}, "create-source-0001")
        self.assertEqual(first, second)

    def test_source_starts_quarantined(self) -> None:
        source = self.store.create_source(SOURCE, "create-source-0002")
        self.assertEqual("QUARANTINED", source["state"])

    def test_approval_activates_source(self) -> None:
        source = self.store.create_source(SOURCE, "create-source-0003")
        approved = self.store.approve_source(source["sourceId"], {"approvedBy": "reviewer"}, "approve-source-0003")
        self.assertEqual("ACTIVE", approved["state"])

    def test_ingestion_requires_approval(self) -> None:
        source = self.store.create_source(SOURCE, "create-source-0004")
        with self.assertRaises(InvalidStateError):
            self.store.create_ingestion(source["sourceId"], {"requestedBy": "operator"}, "ingest-source-0004")

    def test_compatibility_requires_active_members(self) -> None:
        source = self.store.create_source(SOURCE, "create-source-0005")
        request = {
            "name": "invalid",
            "product": "ABLESTACK",
            "productVersion": "1.0",
            "members": [{"sourceVersionId": source["sourceVersionId"], "required": True}],
        }
        with self.assertRaises(InvalidStateError):
            self.store.create_compatibility_set(request, "create-compat-0005")

    def test_withdrawal_creates_deletion_job(self) -> None:
        source = self.store.create_source(SOURCE, "create-source-0006")
        job = self.store.withdraw_source(source["sourceId"], "delete-source-0006")
        self.assertEqual("DELETION", job["jobType"])
        self.assertEqual("WITHDRAWN", self.store.get_source(source["sourceId"])["state"])

    def test_evaluation_run_is_idempotent(self) -> None:
        request = {
            "name": "baseline",
            "sourceProfileIds": ["CLOUD_MAIN"],
            "compatibilitySetId": None,
            "providerProfileId": "OPENAI_RAG_DEFAULT_V1",
            "requestedBy": "operator",
        }
        first = self.store.create_evaluation_run(request, "evaluation-run-0001")
        second = self.store.create_evaluation_run(request, "evaluation-run-0001")
        self.assertEqual(first["runId"], second["runId"])

    def test_missing_objects_return_not_found(self) -> None:
        with self.assertRaises(NotFoundError):
            self.store.get_job(uuid4())


if __name__ == "__main__":
    unittest.main()
