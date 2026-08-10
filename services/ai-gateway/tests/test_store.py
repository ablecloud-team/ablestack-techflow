from __future__ import annotations

import unittest
from uuid import UUID, uuid4

from app.store import InvalidBoundaryError, InvalidStateError, MemoryStore, NotFoundError


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

    def scan(self, source: dict[str, object], *, blocking: int = 0) -> dict[str, object]:
        files = [
            {
                "path": "src/main.py",
                "path_hash": "1" * 64,
                "blob_sha": "b" * 40,
                "content_hash": "2" * 64,
                "size_bytes": 12,
                "source_kind": "SOURCE_CODE",
                "encoding": "utf-8",
                "decision": "ELIGIBLE",
                "rule_ids": (),
                "content": "print('ok')\n",
            }
        ]
        if blocking:
            files.append(
                {
                    "path": "secret.txt", "path_hash": "3" * 64, "blob_sha": "c" * 40,
                    "content_hash": "4" * 64, "size_bytes": 30, "source_kind": "SOURCE_CODE",
                    "encoding": "utf-8", "decision": "QUARANTINED", "rule_ids": ("SECRET_GITHUB_TOKEN",),
                    "content": None,
                }
            )
        report = {
            "commit": source["commit"], "treeSha": "d" * 40, "snapshotHash": "5" * 64,
            "candidateFileCount": len(files), "eligibleFileCount": 1, "excludedFileCount": 0,
            "blockingViolationCount": blocking, "files": files,
        }
        return self.store.record_scan(source["sourceVersionId"], report, "source-fetcher", f"scan-{source['sourceVersionId']}")

    def test_create_source_is_idempotent(self) -> None:
        first = self.store.create_source(SOURCE, "create-source-0001")
        second = self.store.create_source(SOURCE, "create-source-0001")
        self.assertEqual(first, second)

    def test_source_starts_registered(self) -> None:
        source = self.store.create_source(SOURCE, "create-source-0002")
        self.assertEqual("REGISTERED", source["state"])

    def test_scan_and_approval_do_not_activate_before_indexing(self) -> None:
        source = self.store.create_source(SOURCE, "create-source-0003")
        self.assertEqual("QUARANTINED", self.scan(source)["state"])
        approved = self.store.approve_source(
            source["sourceId"], {"approvedBy": "dhslove", "expectedCommit": source["commit"]}, "approve-source-0003"
        )
        self.assertEqual("APPROVED", approved["state"])

    def test_ingestion_requires_approval(self) -> None:
        source = self.store.create_source(SOURCE, "create-source-0004")
        with self.assertRaises(InvalidStateError):
            self.store.create_ingestion(source["sourceId"], {"requestedBy": "operator"}, "ingest-source-0004")

    def test_blocking_finding_and_wrong_reviewer_fail_closed(self) -> None:
        source = self.store.create_source(SOURCE, "create-source-blocked")
        self.scan(source, blocking=1)
        with self.assertRaises(InvalidStateError):
            self.store.approve_version(
                source["sourceVersionId"], {"approvedBy": "dhslove", "expectedCommit": source["commit"]},
                "approve-blocked-source",
            )
        accepted = self.store.approve_version(
            source["sourceVersionId"],
            {
                "approvedBy": "dhslove", "expectedCommit": source["commit"],
                "acceptQuarantineExclusions": True, "decisionNote": "검역 파일을 제외하고 승인",
            },
            "approve-blocked-exclusions",
        )
        self.assertTrue(accepted["quarantineExclusionsAccepted"])
        clean = self.store.create_source({**SOURCE, "commit": "e" * 40}, "create-source-clean")
        self.scan(clean)
        with self.assertRaises(InvalidBoundaryError):
            self.store.approve_version(
                clean["sourceVersionId"], {"approvedBy": "other-reviewer", "expectedCommit": clean["commit"]},
                "approve-wrong-reviewer",
            )

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

    def test_atomic_activation_rejects_partial_indexing(self) -> None:
        source = self.store.create_source(SOURCE, "create-source-index")
        self.scan(source)
        self.store.approve_version(
            source["sourceVersionId"], {"approvedBy": "dhslove", "expectedCommit": source["commit"]},
            "approve-source-index",
        )
        job = self.store.create_ingestion(source["sourceId"], {"requestedBy": "indexer"}, "ingest-source-index")
        with self.assertRaises(Exception):
            self.store.complete_job(
                job["jobId"], {"succeeded": True, "indexedFileCount": 0, "errorCode": None}, "complete-partial"
            )
        completed = self.store.complete_job(
            job["jobId"], {"succeeded": True, "indexedFileCount": 1, "errorCode": None}, "complete-full"
        )
        self.assertEqual("SUCCEEDED", completed["state"])
        self.assertEqual("ACTIVE", self.store.get_source_version(source["sourceVersionId"])["state"])

        reindex = self.store.create_ingestion(
            source["sourceId"], {"requestedBy": "indexer"}, "reindex-active-source"
        )
        self.assertEqual("REINDEX", reindex["jobType"])
        self.assertEqual("ACTIVE", self.store.get_source_version(source["sourceVersionId"])["state"])

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
