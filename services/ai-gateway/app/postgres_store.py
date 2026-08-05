"""PostgreSQL implementation of the Issue #41 persistence boundary."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from .config import Settings
from .source_registry import SOURCE_PROFILES, get_profile, list_profiles, validate_candidate_contract
from .store import ConflictError, InvalidBoundaryError, InvalidStateError, NotFoundError


class PostgresStore:
    def __init__(self, settings: Settings) -> None:
        try:
            from psycopg.rows import dict_row
            from psycopg_pool import ConnectionPool
        except ImportError as exc:  # pragma: no cover - exercised by container validation
            raise RuntimeError("psycopg[binary,pool] is required for postgres mode") from exc
        self._pool = ConnectionPool(
            conninfo=settings.database_dsn or "",
            min_size=settings.database_pool_min,
            max_size=settings.database_pool_max,
            open=False,
            kwargs={"row_factory": dict_row, "application_name": "techflow-ai-gateway"},
            check=ConnectionPool.check_connection,
            timeout=5,
        )
        self._pool.open(wait=True, timeout=10)

    def close(self) -> None:
        self._pool.close()

    def health(self) -> dict[str, str]:
        try:
            with self._pool.connection(timeout=3) as connection:
                row = connection.execute(
                    "SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') AS vector_ready"
                ).fetchone()
            return {
                "process": "ready",
                "database": "ready",
                "vector": "ready" if row and row["vector_ready"] else "missing",
                "provider": "mock",
            }
        except Exception:
            return {"process": "ready", "database": "unavailable", "vector": "unknown", "provider": "mock"}

    @staticmethod
    def _source_payload(row: dict[str, Any]) -> dict[str, Any]:
        return {
            "sourceId": row["source_id"],
            "sourceVersionId": row["source_version_id"],
            "sourceProfileId": row["source_profile_id"],
            "repository": row["repository"],
            "branch": row["branch"],
            "commit": row["commit_sha"],
            "sourceKind": row["source_kind"],
            "classification": row["classification"],
            "licenseSpdx": row["license_spdx"],
            "owner": row.get("owner"),
            "retentionPolicy": row.get("retention_policy"),
            "initialReviewer": row.get("initial_reviewer"),
            "treeSha": row.get("tree_sha"),
            "snapshotHash": row.get("snapshot_hash"),
            "state": row["version_state"],
            "detectedBy": row.get("detected_by"),
            "scannedBy": row.get("scanned_by"),
            "candidateFileCount": row.get("candidate_file_count"),
            "eligibleFileCount": row.get("eligible_file_count"),
            "excludedFileCount": row.get("excluded_file_count"),
            "blockingViolationCount": row.get("blocking_violation_count"),
            "indexedFileCount": row.get("indexed_file_count"),
            "quarantineExclusionsAccepted": row.get("quarantine_exclusions_accepted", False),
            "createdAt": row["created_at"],
            "scannedAt": row.get("scanned_at"),
            "approvedAt": row["approved_at"],
            "approvedBy": row["approved_by"],
        }

    @staticmethod
    def _job_payload(row: dict[str, Any]) -> dict[str, Any]:
        return {
            "jobId": row.get("job_id", row.get("id")),
            "jobType": row["job_type"],
            "sourceId": row["source_id"],
            "sourceVersionId": row["source_version_id"],
            "state": row["state"],
            "failureClass": row["failure_class"],
            "errorCode": row["error_code"],
            "requestedBy": row["requested_by"],
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
        }

    def _source_by_version(self, connection: Any, version_id: UUID) -> dict[str, Any]:
        row = connection.execute(
            """
            SELECT s.id AS source_id, v.id AS source_version_id, s.source_profile_id,
                   s.repository, s.branch, v.commit_sha, s.source_kind, s.classification,
                   s.license_spdx, s.owner, s.retention_policy, s.initial_reviewer,
                   v.tree_sha, v.snapshot_hash, v.state AS version_state, v.detected_by, v.scanned_by,
                   v.candidate_file_count, v.eligible_file_count, v.excluded_file_count,
                   v.blocking_violation_count, v.indexed_file_count, v.quarantine_exclusions_accepted,
                   v.created_at, v.scanned_at,
                   v.approved_at, v.approved_by
            FROM rag_source s JOIN rag_source_version v ON v.source_id = s.id
            WHERE v.id = %s
            """,
            (version_id,),
        ).fetchone()
        if not row:
            raise NotFoundError("source version not found")
        return self._source_payload(row)

    def list_source_profiles(self) -> list[dict[str, Any]]:
        profile_ids = list(SOURCE_PROFILES)
        with self._pool.connection() as connection:
            rows = connection.execute(
                """
                SELECT source_profile_id, owner, repository, branch, source_kind, classification,
                       license_spdx, retention_policy, initial_reviewer
                FROM rag_source WHERE source_profile_id = ANY(%s) ORDER BY source_profile_id
                """,
                (profile_ids,),
            ).fetchall()
        if len(rows) != 9:
            raise InvalidBoundaryError("database source registry is incomplete")
        return [
            {
                "sourceProfileId": row["source_profile_id"], "owner": row["owner"],
                "repository": row["repository"], "branch": row["branch"], "sourceKind": row["source_kind"],
                "classification": row["classification"], "licenseSpdx": row["license_spdx"],
                "retentionPolicy": row["retention_policy"], "initialReviewer": row["initial_reviewer"],
                "docsRoot": next(item["docsRoot"] for item in list_profiles() if item["sourceProfileId"] == row["source_profile_id"]),
            }
            for row in rows
        ]

    def register_candidate(
        self, profile_id: str, commit: str, detected_by: str, idempotency_key: str
    ) -> dict[str, Any]:
        profile = get_profile(profile_id)
        with self._pool.connection() as connection:
            repeated = connection.execute(
                "SELECT id FROM rag_source_version WHERE create_idempotency_key=%s", (idempotency_key,)
            ).fetchone()
            if repeated:
                return self._source_by_version(connection, repeated["id"])
            source = connection.execute(
                "SELECT id, repository, branch, source_kind, classification, initial_reviewer FROM rag_source WHERE source_profile_id=%s FOR UPDATE",
                (profile_id,),
            ).fetchone()
            if not source:
                raise NotFoundError("source profile is not registered")
            if (
                source["repository"], source["branch"], source["source_kind"], source["classification"], source["initial_reviewer"]
            ) != (profile.repository, profile.branch, profile.source_kind, profile.classification, profile.initial_reviewer):
                raise InvalidBoundaryError("database source profile differs from immutable registry")
            existing = connection.execute(
                "SELECT id FROM rag_source_version WHERE source_id=%s AND commit_sha=%s", (source["id"], commit)
            ).fetchone()
            if existing:
                return self._source_by_version(connection, existing["id"])
            version_id = uuid4()
            connection.execute(
                """
                INSERT INTO rag_source_version
                    (id, source_id, commit_sha, state, create_idempotency_key, detected_by)
                VALUES (%s, %s, %s, 'REGISTERED', %s, %s)
                """,
                (version_id, source["id"], commit, idempotency_key, detected_by),
            )
            connection.execute("UPDATE rag_source SET state='REGISTERED', updated_at=now() WHERE id=%s", (source["id"],))
            return self._source_by_version(connection, version_id)

    def create_source(self, request: dict[str, Any], idempotency_key: str) -> dict[str, Any]:
        profile = validate_candidate_contract(request)
        return self.register_candidate(profile.profile_id, request["commit"], "manual-api", idempotency_key)

    def get_source(self, source_id: UUID) -> dict[str, Any]:
        with self._pool.connection() as connection:
            row = connection.execute(
                """
                SELECT s.id AS source_id, v.id AS source_version_id, s.source_profile_id,
                       s.repository, s.branch, v.commit_sha, s.source_kind, s.classification,
                       s.license_spdx, s.owner, s.retention_policy, s.initial_reviewer,
                       v.tree_sha, v.snapshot_hash, v.state AS version_state, v.detected_by, v.scanned_by,
                       v.candidate_file_count, v.eligible_file_count, v.excluded_file_count,
                       v.blocking_violation_count, v.indexed_file_count, v.quarantine_exclusions_accepted,
                       v.created_at, v.scanned_at,
                       v.approved_at, v.approved_by
                FROM rag_source s JOIN rag_source_version v ON v.source_id = s.id
                WHERE s.id = %s ORDER BY v.created_at DESC LIMIT 1
                """,
                (source_id,),
            ).fetchone()
            if not row:
                raise NotFoundError("source not found")
            return self._source_payload(row)

    def get_source_version(self, version_id: UUID) -> dict[str, Any]:
        with self._pool.connection() as connection:
            return self._source_by_version(connection, version_id)

    def record_scan(
        self, version_id: UUID, report: dict[str, Any], scanned_by: str, idempotency_key: str
    ) -> dict[str, Any]:
        with self._pool.connection() as connection:
            repeated = connection.execute(
                "SELECT id FROM rag_source_version WHERE scan_idempotency_key=%s", (idempotency_key,)
            ).fetchone()
            if repeated:
                return self._source_by_version(connection, repeated["id"])
            version = connection.execute(
                """
                SELECT v.id, v.source_id, v.commit_sha, v.state, v.snapshot_hash, s.repository
                FROM rag_source_version v JOIN rag_source s ON s.id=v.source_id
                WHERE v.id=%s FOR UPDATE
                """,
                (version_id,),
            ).fetchone()
            if not version:
                raise NotFoundError("source version not found")
            if version["state"] == "QUARANTINED" and version["snapshot_hash"] == report["snapshotHash"]:
                return self._source_by_version(connection, version_id)
            if version["state"] != "REGISTERED":
                raise InvalidStateError("only registered candidates can be scanned")
            if version["commit_sha"] != report["commit"]:
                raise ConflictError("scan commit differs from registered candidate")
            if connection.execute(
                "SELECT 1 FROM rag_source_file WHERE source_version_id=%s", (version_id,)
            ).fetchone():
                raise ConflictError("source version scan inventory already exists")
            for raw_file in report["files"]:
                content = raw_file.get("content")
                blob_id = None
                if raw_file["decision"] == "ELIGIBLE":
                    if not raw_file.get("blob_sha") or content is None:
                        raise InvalidBoundaryError("eligible file is missing verified blob content")
                    existing_blob = connection.execute(
                        "SELECT id, content_hash FROM rag_source_blob WHERE repository=%s AND blob_sha=%s",
                        (version["repository"], raw_file["blob_sha"]),
                    ).fetchone()
                    if existing_blob and existing_blob["content_hash"] != raw_file["content_hash"]:
                        raise ConflictError("blob SHA content hash mismatch")
                    if existing_blob:
                        blob_id = existing_blob["id"]
                    else:
                        blob_id = uuid4()
                        connection.execute(
                            """
                            INSERT INTO rag_source_blob
                                (id, repository, blob_sha, content_hash, size_bytes, encoding, classification, content)
                            VALUES (%s, %s, %s, %s, %s, 'utf-8', 'D0', %s)
                            """,
                            (
                                blob_id, version["repository"], raw_file["blob_sha"], raw_file["content_hash"],
                                raw_file["size_bytes"], content,
                            ),
                        )
                connection.execute(
                    """
                    INSERT INTO rag_source_file
                        (id, source_version_id, path, path_hash, blob_sha, source_blob_id, content_hash,
                         size_bytes, source_kind, encoding, decision, rule_ids)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        uuid4(), version_id, raw_file["path"], raw_file["path_hash"], raw_file.get("blob_sha"),
                        blob_id, raw_file.get("content_hash"), raw_file.get("size_bytes"), raw_file.get("source_kind"),
                        raw_file.get("encoding"), raw_file["decision"], list(raw_file.get("rule_ids") or ()),
                    ),
                )
                severity = "BLOCKING" if raw_file["decision"] == "QUARANTINED" else "INFO"
                for rule_id in raw_file.get("rule_ids") or ():
                    connection.execute(
                        """
                        INSERT INTO rag_source_scan_finding (id, source_version_id, path_hash, rule_id, severity)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (uuid4(), version_id, raw_file["path_hash"], rule_id, severity),
                    )
            connection.execute(
                """
                UPDATE rag_source_version SET
                    state='QUARANTINED', tree_sha=%s, snapshot_hash=%s, scanned_by=%s,
                    scan_idempotency_key=%s, scanned_at=now(),
                    candidate_file_count=%s, eligible_file_count=%s, excluded_file_count=%s,
                    blocking_violation_count=%s
                WHERE id=%s
                """,
                (
                    report["treeSha"], report["snapshotHash"], scanned_by, idempotency_key, report["candidateFileCount"],
                    report["eligibleFileCount"], report["excludedFileCount"], report["blockingViolationCount"], version_id,
                ),
            )
            connection.execute(
                "UPDATE rag_source SET state='QUARANTINED', updated_at=now() WHERE id=%s", (version["source_id"],)
            )
            return self._source_by_version(connection, version_id)

    def list_source_files(self, version_id: UUID) -> list[dict[str, Any]]:
        with self._pool.connection() as connection:
            if not connection.execute("SELECT 1 FROM rag_source_version WHERE id=%s", (version_id,)).fetchone():
                raise NotFoundError("source version not found")
            rows = connection.execute(
                """
                SELECT path, path_hash, blob_sha, content_hash, size_bytes, source_kind, encoding, decision, rule_ids
                FROM rag_source_file WHERE source_version_id=%s ORDER BY path
                """,
                (version_id,),
            ).fetchall()
        return [
            {
                "path": row["path"], "pathHash": row["path_hash"], "blobSha": row["blob_sha"],
                "contentHash": row["content_hash"], "sizeBytes": row["size_bytes"], "sourceKind": row["source_kind"],
                "encoding": row["encoding"], "decision": row["decision"], "ruleIds": row["rule_ids"],
            }
            for row in rows
        ]

    def approve_version(self, version_id: UUID, request: dict[str, Any], idempotency_key: str) -> dict[str, Any]:
        with self._pool.connection() as connection:
            repeated = connection.execute(
                "SELECT id FROM rag_source_version WHERE approval_idempotency_key=%s", (idempotency_key,)
            ).fetchone()
            if repeated:
                return self._source_by_version(connection, repeated["id"])
            row = connection.execute(
                """
                SELECT v.id, v.source_id, v.commit_sha, v.state, v.blocking_violation_count,
                       s.source_profile_id, s.initial_reviewer
                FROM rag_source_version v JOIN rag_source s ON s.id=v.source_id
                WHERE v.id=%s FOR UPDATE
                """,
                (version_id,),
            ).fetchone()
            if not row:
                raise NotFoundError("source version not found")
            if row["state"] != "QUARANTINED":
                raise InvalidStateError("only quarantined source versions can be approved")
            if row["blocking_violation_count"] != 0 and not request.get("acceptQuarantineExclusions", False):
                raise InvalidStateError("blocking quarantine exclusions require explicit reviewer acceptance")
            if request.get("expectedCommit") and request["expectedCommit"] != row["commit_sha"]:
                raise ConflictError("approval commit differs from scanned candidate")
            if request["approvedBy"] != row["initial_reviewer"]:
                raise InvalidBoundaryError("reviewer is not authorized for this source profile")
            connection.execute(
                """
                UPDATE rag_source_version SET state='APPROVED', approved_at=now(), approved_by=%s,
                    approval_note=%s, approval_idempotency_key=%s, quarantine_exclusions_accepted=%s WHERE id=%s
                """,
                (
                    request["approvedBy"], request.get("decisionNote"), idempotency_key,
                    request.get("acceptQuarantineExclusions", False), version_id,
                ),
            )
            connection.execute("UPDATE rag_source SET state='APPROVED', updated_at=now() WHERE id=%s", (row["source_id"],))
            return self._source_by_version(connection, version_id)

    def approve_source(self, source_id: UUID, request: dict[str, Any], idempotency_key: str) -> dict[str, Any]:
        with self._pool.connection() as connection:
            row = connection.execute(
                "SELECT id FROM rag_source_version WHERE source_id = %s ORDER BY created_at DESC LIMIT 1",
                (source_id,),
            ).fetchone()
            if not row:
                raise NotFoundError("source not found")
            version_id = row["id"]
        return self.approve_version(version_id, request, idempotency_key)

    def create_compatibility_set(self, request: dict[str, Any], idempotency_key: str) -> dict[str, Any]:
        with self._pool.connection() as connection:
            repeated = connection.execute(
                "SELECT id, name, product, product_version, state, created_at FROM rag_compatibility_set WHERE idempotency_key=%s",
                (idempotency_key,),
            ).fetchone()
            if repeated:
                members = connection.execute(
                    "SELECT source_version_id, required FROM rag_compatibility_set_source WHERE compatibility_set_id=%s ORDER BY source_version_id",
                    (repeated["id"],),
                ).fetchall()
                return self._compatibility_payload(repeated, members)
            member_ids = [UUID(str(member["sourceVersionId"])) for member in request["members"]]
            active = connection.execute(
                "SELECT id FROM rag_source_version WHERE id = ANY(%s) AND state='ACTIVE' AND approved_at IS NOT NULL",
                (member_ids,),
            ).fetchall()
            if {row["id"] for row in active} != set(member_ids):
                raise InvalidStateError("compatibility members must be active approved source versions")
            set_id = uuid4()
            row = connection.execute(
                """
                INSERT INTO rag_compatibility_set (id, name, product, product_version, state, idempotency_key)
                VALUES (%s, %s, %s, %s, 'APPROVED', %s)
                RETURNING id, name, product, product_version, state, created_at
                """,
                (set_id, request["name"], request["product"], request["productVersion"], idempotency_key),
            ).fetchone()
            for member in request["members"]:
                connection.execute(
                    "INSERT INTO rag_compatibility_set_source (compatibility_set_id, source_version_id, required) VALUES (%s, %s, %s)",
                    (set_id, member["sourceVersionId"], member["required"]),
                )
            return self._compatibility_payload(row, request["members"])

    @staticmethod
    def _compatibility_payload(row: dict[str, Any], members: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "compatibilitySetId": row["id"],
            "name": row["name"],
            "product": row["product"],
            "productVersion": row["product_version"],
            "state": row["state"],
            "createdAt": row["created_at"],
            "members": [
                {
                    "sourceVersionId": member.get("source_version_id", member.get("sourceVersionId")),
                    "required": member["required"],
                }
                for member in members
            ],
        }

    def create_ingestion(self, source_id: UUID, request: dict[str, Any], idempotency_key: str) -> dict[str, Any]:
        with self._pool.connection() as connection:
            repeated = connection.execute(
                "SELECT * FROM rag_ingestion_job WHERE idempotency_key=%s", (idempotency_key,)
            ).fetchone()
            if repeated:
                return self._job_payload(repeated)
            version = connection.execute(
                "SELECT id FROM rag_source_version WHERE source_id=%s AND state='APPROVED' ORDER BY created_at DESC LIMIT 1 FOR UPDATE",
                (source_id,),
            ).fetchone()
            if not version:
                raise InvalidStateError("source must be approved before indexing")
            connection.execute("UPDATE rag_source_version SET state='INDEXING' WHERE id=%s", (version["id"],))
            connection.execute("UPDATE rag_source SET state='INDEXING', updated_at=now() WHERE id=%s", (source_id,))
            row = connection.execute(
                """
                INSERT INTO rag_ingestion_job
                    (id, job_type, source_id, source_version_id, state, requested_by, idempotency_key)
                VALUES (%s, 'INGESTION', %s, %s, 'PENDING', %s, %s)
                RETURNING *
                """,
                (uuid4(), source_id, version["id"], request["requestedBy"], idempotency_key),
            ).fetchone()
            return self._job_payload(row)

    def complete_job(self, job_id: UUID, request: dict[str, Any], idempotency_key: str) -> dict[str, Any]:
        with self._pool.connection() as connection:
            repeated = connection.execute(
                "SELECT * FROM rag_ingestion_job WHERE completion_idempotency_key=%s", (idempotency_key,)
            ).fetchone()
            if repeated:
                return self._job_payload(repeated)
            job = connection.execute(
                "SELECT * FROM rag_ingestion_job WHERE id=%s FOR UPDATE", (job_id,)
            ).fetchone()
            if not job:
                raise NotFoundError("job not found")
            if job["job_type"] != "INGESTION" or job["state"] not in {"PENDING", "RUNNING"}:
                raise InvalidStateError("job cannot complete indexing")
            version = connection.execute(
                "SELECT id, source_id, state, eligible_file_count FROM rag_source_version WHERE id=%s FOR UPDATE",
                (job["source_version_id"],),
            ).fetchone()
            if not version or version["state"] != "INDEXING":
                raise InvalidStateError("source version is not indexing")
            if request["succeeded"]:
                if request["indexedFileCount"] != version["eligible_file_count"]:
                    raise ConflictError("partial indexing cannot activate a source version")
                connection.execute(
                    "UPDATE rag_source_version SET state='WITHDRAWN' WHERE source_id=%s AND state='ACTIVE' AND id<>%s",
                    (version["source_id"], version["id"]),
                )
                connection.execute(
                    "UPDATE rag_source_version SET state='ACTIVE', indexed_file_count=%s WHERE id=%s",
                    (request["indexedFileCount"], version["id"]),
                )
                connection.execute("UPDATE rag_source SET state='ACTIVE', updated_at=now() WHERE id=%s", (version["source_id"],))
                updated = connection.execute(
                    """
                    UPDATE rag_ingestion_job SET state='SUCCEEDED', failure_class=NULL, error_code=NULL,
                        completion_idempotency_key=%s, updated_at=now() WHERE id=%s RETURNING *
                    """,
                    (idempotency_key, job_id),
                ).fetchone()
            else:
                connection.execute("UPDATE rag_source_version SET state='APPROVED' WHERE id=%s", (version["id"],))
                connection.execute("UPDATE rag_source SET state='APPROVED', updated_at=now() WHERE id=%s", (version["source_id"],))
                updated = connection.execute(
                    """
                    UPDATE rag_ingestion_job SET state='FAILED', failure_class='TERMINAL', error_code=%s,
                        completion_idempotency_key=%s, updated_at=now() WHERE id=%s RETURNING *
                    """,
                    (request["errorCode"], idempotency_key, job_id),
                ).fetchone()
            return self._job_payload(updated)

    def withdraw_source(self, source_id: UUID, idempotency_key: str) -> dict[str, Any]:
        with self._pool.connection() as connection:
            repeated = connection.execute(
                "SELECT * FROM rag_ingestion_job WHERE idempotency_key=%s", (idempotency_key,)
            ).fetchone()
            if repeated:
                return self._job_payload(repeated)
            version = connection.execute(
                "SELECT id FROM rag_source_version WHERE source_id=%s ORDER BY created_at DESC LIMIT 1 FOR UPDATE",
                (source_id,),
            ).fetchone()
            if not version:
                raise NotFoundError("source not found")
            connection.execute("UPDATE rag_source SET state='WITHDRAWN', updated_at=now() WHERE id=%s", (source_id,))
            connection.execute("UPDATE rag_source_version SET state='WITHDRAWN' WHERE source_id=%s", (source_id,))
            job_id = uuid4()
            row = connection.execute(
                """
                INSERT INTO rag_ingestion_job
                    (id, job_type, source_id, source_version_id, state, requested_by, idempotency_key)
                VALUES (%s, 'DELETION', %s, %s, 'PENDING', 'system', %s)
                RETURNING *
                """,
                (job_id, source_id, version["id"], idempotency_key),
            ).fetchone()
            connection.execute(
                """
                INSERT INTO rag_deletion_ledger
                    (id, source_id, source_version_id, job_id, state, excluded_at, policy_deadline_at)
                VALUES (%s, %s, %s, %s, 'PENDING', now(), now() + interval '7 days')
                """,
                (uuid4(), source_id, version["id"], job_id),
            )
            return self._job_payload(row)

    def get_job(self, job_id: UUID) -> dict[str, Any]:
        with self._pool.connection() as connection:
            row = connection.execute("SELECT * FROM rag_ingestion_job WHERE id=%s", (job_id,)).fetchone()
            if not row:
                raise NotFoundError("job not found")
            return self._job_payload(row)

    def create_evaluation_run(self, request: dict[str, Any], idempotency_key: str) -> dict[str, Any]:
        with self._pool.connection() as connection:
            repeated = connection.execute(
                "SELECT * FROM rag_evaluation_run WHERE idempotency_key=%s", (idempotency_key,)
            ).fetchone()
            if repeated:
                return self._evaluation_payload(repeated)
            row = connection.execute(
                """
                INSERT INTO rag_evaluation_run
                    (id, name, source_profile_ids, compatibility_set_id, provider_profile_id,
                     requested_by, state, idempotency_key)
                VALUES (%s, %s, %s, %s, %s, %s, 'PENDING', %s)
                RETURNING *
                """,
                (
                    uuid4(),
                    request["name"],
                    request.get("sourceProfileIds"),
                    request.get("compatibilitySetId"),
                    request["providerProfileId"],
                    request["requestedBy"],
                    idempotency_key,
                ),
            ).fetchone()
            return self._evaluation_payload(row)

    @staticmethod
    def _evaluation_payload(row: dict[str, Any]) -> dict[str, Any]:
        return {
            "runId": row["id"],
            "name": row["name"],
            "sourceProfileIds": row["source_profile_ids"],
            "compatibilitySetId": row["compatibility_set_id"],
            "providerProfileId": row["provider_profile_id"],
            "requestedBy": row["requested_by"],
            "state": row["state"],
            "totalCases": row["total_cases"],
            "passedCases": row["passed_cases"],
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
        }

    def get_evaluation_run(self, run_id: UUID) -> dict[str, Any]:
        with self._pool.connection() as connection:
            row = connection.execute("SELECT * FROM rag_evaluation_run WHERE id=%s", (run_id,)).fetchone()
            if not row:
                raise NotFoundError("evaluation run not found")
            return self._evaluation_payload(row)
