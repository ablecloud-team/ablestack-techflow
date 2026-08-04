"""Storage interface and deterministic in-memory implementation."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Protocol
from uuid import UUID, uuid4


class StoreError(RuntimeError):
    code = "STORE_ERROR"
    http_status = 500


class NotFoundError(StoreError):
    code = "NOT_FOUND"
    http_status = 404


class ConflictError(StoreError):
    code = "CONFLICT"
    http_status = 409


class InvalidStateError(StoreError):
    code = "INVALID_STATE"
    http_status = 409


class InvalidBoundaryError(StoreError):
    code = "INVALID_BOUNDARY"
    http_status = 400


class Store(Protocol):
    def health(self) -> dict[str, str]: ...
    def close(self) -> None: ...
    def create_source(self, request: dict[str, Any], idempotency_key: str) -> dict[str, Any]: ...
    def get_source(self, source_id: UUID) -> dict[str, Any]: ...
    def approve_source(self, source_id: UUID, request: dict[str, Any], idempotency_key: str) -> dict[str, Any]: ...
    def create_compatibility_set(self, request: dict[str, Any], idempotency_key: str) -> dict[str, Any]: ...
    def create_ingestion(self, source_id: UUID, request: dict[str, Any], idempotency_key: str) -> dict[str, Any]: ...
    def withdraw_source(self, source_id: UUID, idempotency_key: str) -> dict[str, Any]: ...
    def get_job(self, job_id: UUID) -> dict[str, Any]: ...
    def create_evaluation_run(self, request: dict[str, Any], idempotency_key: str) -> dict[str, Any]: ...
    def get_evaluation_run(self, run_id: UUID) -> dict[str, Any]: ...


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MemoryStore:
    """Thread-safe store used by unit tests and the non-network PoC canary."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._sources: dict[UUID, dict[str, Any]] = {}
        self._source_versions: dict[UUID, dict[str, Any]] = {}
        self._compatibility_sets: dict[UUID, dict[str, Any]] = {}
        self._jobs: dict[UUID, dict[str, Any]] = {}
        self._evaluation_runs: dict[UUID, dict[str, Any]] = {}
        self._idempotency: dict[tuple[str, str], dict[str, Any]] = {}

    def _repeat(self, operation: str, key: str) -> dict[str, Any] | None:
        value = self._idempotency.get((operation, key))
        return deepcopy(value) if value else None

    def _remember(self, operation: str, key: str, value: dict[str, Any]) -> dict[str, Any]:
        self._idempotency[(operation, key)] = deepcopy(value)
        return deepcopy(value)

    def health(self) -> dict[str, str]:
        return {"process": "ready", "database": "ready", "vector": "ready", "provider": "mock"}

    def close(self) -> None:
        return None

    def create_source(self, request: dict[str, Any], idempotency_key: str) -> dict[str, Any]:
        with self._lock:
            if repeated := self._repeat("create_source", idempotency_key):
                return repeated
            profile_id = request["sourceProfileId"]
            if any(item["sourceProfileId"] == profile_id for item in self._sources.values()):
                raise ConflictError("source profile already exists")
            source_id, version_id, created_at = uuid4(), uuid4(), utc_now()
            source = {
                "sourceId": source_id,
                "sourceVersionId": version_id,
                **request,
                "state": "QUARANTINED",
                "createdAt": created_at,
                "approvedAt": None,
                "approvedBy": None,
            }
            self._sources[source_id] = source
            self._source_versions[version_id] = source
            return self._remember("create_source", idempotency_key, source)

    def get_source(self, source_id: UUID) -> dict[str, Any]:
        with self._lock:
            if source_id not in self._sources:
                raise NotFoundError("source not found")
            return deepcopy(self._sources[source_id])

    def approve_source(self, source_id: UUID, request: dict[str, Any], idempotency_key: str) -> dict[str, Any]:
        with self._lock:
            if repeated := self._repeat("approve_source", idempotency_key):
                return repeated
            source = self._sources.get(source_id)
            if not source:
                raise NotFoundError("source not found")
            if source["state"] != "QUARANTINED":
                raise InvalidStateError("only quarantined sources can be approved")
            source.update({"state": "ACTIVE", "approvedAt": utc_now(), "approvedBy": request["approvedBy"]})
            return self._remember("approve_source", idempotency_key, source)

    def create_compatibility_set(self, request: dict[str, Any], idempotency_key: str) -> dict[str, Any]:
        with self._lock:
            if repeated := self._repeat("create_compatibility_set", idempotency_key):
                return repeated
            for member in request["members"]:
                version = self._source_versions.get(UUID(str(member["sourceVersionId"])))
                if not version or version["state"] != "ACTIVE":
                    raise InvalidStateError("compatibility members must be active approved source versions")
            set_id = uuid4()
            value = {
                "compatibilitySetId": set_id,
                **request,
                "state": "APPROVED",
                "createdAt": utc_now(),
            }
            self._compatibility_sets[set_id] = value
            return self._remember("create_compatibility_set", idempotency_key, value)

    def create_ingestion(self, source_id: UUID, request: dict[str, Any], idempotency_key: str) -> dict[str, Any]:
        with self._lock:
            if repeated := self._repeat("create_ingestion", idempotency_key):
                return repeated
            source = self._sources.get(source_id)
            if not source:
                raise NotFoundError("source not found")
            if source["state"] != "ACTIVE":
                raise InvalidStateError("source must be active before ingestion")
            job_id = uuid4()
            value = {
                "jobId": job_id,
                "jobType": "INGESTION",
                "sourceId": source_id,
                "sourceVersionId": source["sourceVersionId"],
                "state": "PENDING",
                "failureClass": None,
                "errorCode": None,
                "requestedBy": request["requestedBy"],
                "createdAt": utc_now(),
                "updatedAt": utc_now(),
            }
            self._jobs[job_id] = value
            return self._remember("create_ingestion", idempotency_key, value)

    def withdraw_source(self, source_id: UUID, idempotency_key: str) -> dict[str, Any]:
        with self._lock:
            if repeated := self._repeat("withdraw_source", idempotency_key):
                return repeated
            source = self._sources.get(source_id)
            if not source:
                raise NotFoundError("source not found")
            source["state"] = "WITHDRAWN"
            job_id = uuid4()
            value = {
                "jobId": job_id,
                "jobType": "DELETION",
                "sourceId": source_id,
                "sourceVersionId": source["sourceVersionId"],
                "state": "PENDING",
                "failureClass": None,
                "errorCode": None,
                "requestedBy": "system",
                "createdAt": utc_now(),
                "updatedAt": utc_now(),
            }
            self._jobs[job_id] = value
            return self._remember("withdraw_source", idempotency_key, value)

    def get_job(self, job_id: UUID) -> dict[str, Any]:
        with self._lock:
            if job_id not in self._jobs:
                raise NotFoundError("job not found")
            return deepcopy(self._jobs[job_id])

    def create_evaluation_run(self, request: dict[str, Any], idempotency_key: str) -> dict[str, Any]:
        with self._lock:
            if repeated := self._repeat("create_evaluation_run", idempotency_key):
                return repeated
            run_id = uuid4()
            value = {
                "runId": run_id,
                **request,
                "state": "PENDING",
                "totalCases": 0,
                "passedCases": 0,
                "createdAt": utc_now(),
                "updatedAt": utc_now(),
            }
            self._evaluation_runs[run_id] = value
            return self._remember("create_evaluation_run", idempotency_key, value)

    def get_evaluation_run(self, run_id: UUID) -> dict[str, Any]:
        with self._lock:
            if run_id not in self._evaluation_runs:
                raise NotFoundError("evaluation run not found")
            return deepcopy(self._evaluation_runs[run_id])
