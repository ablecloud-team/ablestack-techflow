"""PostgreSQL implementation of the Issue #41 persistence boundary."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from .config import Settings
from .store import ConflictError, InvalidStateError, NotFoundError


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
            "state": row["version_state"],
            "createdAt": row["created_at"],
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
                   s.license_spdx, v.state AS version_state, v.created_at, v.approved_at, v.approved_by
            FROM rag_source s JOIN rag_source_version v ON v.source_id = s.id
            WHERE v.id = %s
            """,
            (version_id,),
        ).fetchone()
        if not row:
            raise NotFoundError("source version not found")
        return self._source_payload(row)

    def create_source(self, request: dict[str, Any], idempotency_key: str) -> dict[str, Any]:
        with self._pool.connection() as connection:
            repeated = connection.execute(
                "SELECT id FROM rag_source_version WHERE create_idempotency_key = %s",
                (idempotency_key,),
            ).fetchone()
            if repeated:
                return self._source_by_version(connection, repeated["id"])
            if connection.execute(
                "SELECT 1 FROM rag_source WHERE source_profile_id = %s", (request["sourceProfileId"],)
            ).fetchone():
                raise ConflictError("source profile already exists")
            source_id, version_id = uuid4(), uuid4()
            connection.execute(
                """
                INSERT INTO rag_source
                    (id, source_profile_id, repository, branch, source_kind, classification, license_spdx, state)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'QUARANTINED')
                """,
                (
                    source_id,
                    request["sourceProfileId"],
                    request["repository"],
                    request["branch"],
                    request["sourceKind"],
                    request["classification"],
                    request.get("licenseSpdx"),
                ),
            )
            connection.execute(
                """
                INSERT INTO rag_source_version (id, source_id, commit_sha, state, create_idempotency_key)
                VALUES (%s, %s, %s, 'QUARANTINED', %s)
                """,
                (version_id, source_id, request["commit"], idempotency_key),
            )
            return self._source_by_version(connection, version_id)

    def get_source(self, source_id: UUID) -> dict[str, Any]:
        with self._pool.connection() as connection:
            row = connection.execute(
                """
                SELECT s.id AS source_id, v.id AS source_version_id, s.source_profile_id,
                       s.repository, s.branch, v.commit_sha, s.source_kind, s.classification,
                       s.license_spdx, v.state AS version_state, v.created_at, v.approved_at, v.approved_by
                FROM rag_source s JOIN rag_source_version v ON v.source_id = s.id
                WHERE s.id = %s ORDER BY v.created_at DESC LIMIT 1
                """,
                (source_id,),
            ).fetchone()
            if not row:
                raise NotFoundError("source not found")
            return self._source_payload(row)

    def approve_source(self, source_id: UUID, request: dict[str, Any], idempotency_key: str) -> dict[str, Any]:
        with self._pool.connection() as connection:
            repeated = connection.execute(
                "SELECT id FROM rag_source_version WHERE approval_idempotency_key = %s",
                (idempotency_key,),
            ).fetchone()
            if repeated:
                return self._source_by_version(connection, repeated["id"])
            row = connection.execute(
                "SELECT id, state FROM rag_source_version WHERE source_id = %s ORDER BY created_at DESC LIMIT 1 FOR UPDATE",
                (source_id,),
            ).fetchone()
            if not row:
                raise NotFoundError("source not found")
            if row["state"] != "QUARANTINED":
                raise InvalidStateError("only quarantined sources can be approved")
            connection.execute(
                """
                UPDATE rag_source_version
                SET state='ACTIVE', approved_at=now(), approved_by=%s,
                    approval_note=%s, approval_idempotency_key=%s
                WHERE id=%s
                """,
                (request["approvedBy"], request.get("decisionNote"), idempotency_key, row["id"]),
            )
            connection.execute("UPDATE rag_source SET state='ACTIVE', updated_at=now() WHERE id=%s", (source_id,))
            return self._source_by_version(connection, row["id"])

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
                "SELECT id FROM rag_source_version WHERE source_id=%s AND state='ACTIVE' ORDER BY created_at DESC LIMIT 1",
                (source_id,),
            ).fetchone()
            if not version:
                raise InvalidStateError("source must be active before ingestion")
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
