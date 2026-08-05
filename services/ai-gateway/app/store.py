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
    def list_source_profiles(self) -> list[dict[str, Any]]: ...
    def register_candidate(self, profile_id: str, commit: str, detected_by: str, idempotency_key: str) -> dict[str, Any]: ...
    def get_source_version(self, version_id: UUID) -> dict[str, Any]: ...
    def record_scan(self, version_id: UUID, report: dict[str, Any], scanned_by: str, idempotency_key: str) -> dict[str, Any]: ...
    def list_source_files(self, version_id: UUID) -> list[dict[str, Any]]: ...
    def approve_version(self, version_id: UUID, request: dict[str, Any], idempotency_key: str) -> dict[str, Any]: ...
    def complete_job(self, job_id: UUID, request: dict[str, Any], idempotency_key: str) -> dict[str, Any]: ...
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
        self._source_by_profile: dict[str, UUID] = {}
        self._version_by_profile_commit: dict[tuple[str, str], UUID] = {}
        self._source_files: dict[UUID, dict[str, dict[str, Any]]] = {}
        self._blob_cache: dict[tuple[str, str], dict[str, Any]] = {}
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

    def list_source_profiles(self) -> list[dict[str, Any]]:
        from .source_registry import list_profiles

        return list_profiles()

    def _version_payload(self, version: dict[str, Any]) -> dict[str, Any]:
        return deepcopy(version)

    def _latest_version(self, source_id: UUID) -> dict[str, Any]:
        versions = [item for item in self._source_versions.values() if item["sourceId"] == source_id]
        if not versions:
            raise NotFoundError("source version not found")
        return max(versions, key=lambda item: item["createdAt"])

    def register_candidate(
        self, profile_id: str, commit: str, detected_by: str, idempotency_key: str
    ) -> dict[str, Any]:
        from .source_registry import get_profile

        with self._lock:
            if repeated := self._repeat("register_candidate", idempotency_key):
                return repeated
            profile = get_profile(profile_id)
            existing_id = self._version_by_profile_commit.get((profile_id, commit))
            if existing_id:
                return self._remember("register_candidate", idempotency_key, self._source_versions[existing_id])
            source_id = self._source_by_profile.get(profile_id)
            if source_id is None:
                source_id = uuid4()
                self._source_by_profile[profile_id] = source_id
                self._sources[source_id] = {"sourceId": source_id, **profile.payload()}
            version_id, created_at = uuid4(), utc_now()
            version = {
                "sourceId": source_id,
                "sourceVersionId": version_id,
                **profile.payload(),
                "commit": commit,
                "treeSha": None,
                "snapshotHash": None,
                "state": "REGISTERED",
                "detectedBy": detected_by,
                "candidateFileCount": None,
                "eligibleFileCount": None,
                "excludedFileCount": None,
                "blockingViolationCount": None,
                "indexedFileCount": None,
                "quarantineExclusionsAccepted": False,
                "createdAt": created_at,
                "scannedAt": None,
                "approvedAt": None,
                "approvedBy": None,
            }
            self._source_versions[version_id] = version
            self._version_by_profile_commit[(profile_id, commit)] = version_id
            self._source_files[version_id] = {}
            return self._remember("register_candidate", idempotency_key, version)

    def create_source(self, request: dict[str, Any], idempotency_key: str) -> dict[str, Any]:
        from .source_registry import validate_candidate_contract

        profile = validate_candidate_contract(request)
        return self.register_candidate(profile.profile_id, request["commit"], "manual-api", idempotency_key)

    def get_source(self, source_id: UUID) -> dict[str, Any]:
        with self._lock:
            if source_id not in self._sources:
                raise NotFoundError("source not found")
            return self._version_payload(self._latest_version(source_id))

    def get_source_version(self, version_id: UUID) -> dict[str, Any]:
        with self._lock:
            version = self._source_versions.get(version_id)
            if not version:
                raise NotFoundError("source version not found")
            return self._version_payload(version)

    def record_scan(
        self, version_id: UUID, report: dict[str, Any], scanned_by: str, idempotency_key: str
    ) -> dict[str, Any]:
        with self._lock:
            if repeated := self._repeat("record_scan", idempotency_key):
                return repeated
            version = self._source_versions.get(version_id)
            if not version:
                raise NotFoundError("source version not found")
            if version["state"] != "REGISTERED":
                raise InvalidStateError("only registered candidates can be scanned")
            if report["commit"] != version["commit"]:
                raise ConflictError("scan commit differs from registered candidate")
            records: dict[str, dict[str, Any]] = {}
            repository = version["repository"]
            for raw_file in report["files"]:
                file_record = deepcopy(raw_file)
                content = file_record.pop("content", None)
                blob_sha = file_record.get("blob_sha")
                if file_record["decision"] == "ELIGIBLE" and blob_sha and content is not None:
                    cache_key = (repository, blob_sha)
                    cached = self._blob_cache.get(cache_key)
                    if cached and cached["contentHash"] != file_record["content_hash"]:
                        raise ConflictError("blob SHA content hash mismatch")
                    self._blob_cache.setdefault(
                        cache_key,
                        {"repository": repository, "blobSha": blob_sha, "contentHash": file_record["content_hash"], "content": content},
                    )
                records[file_record["path"]] = {
                    "path": file_record["path"],
                    "pathHash": file_record["path_hash"],
                    "blobSha": blob_sha,
                    "contentHash": file_record.get("content_hash"),
                    "sizeBytes": file_record.get("size_bytes"),
                    "sourceKind": file_record.get("source_kind"),
                    "encoding": file_record.get("encoding"),
                    "decision": file_record["decision"],
                    "ruleIds": list(file_record.get("rule_ids") or ()),
                }
            self._source_files[version_id] = records
            version.update(
                {
                    "treeSha": report["treeSha"],
                    "snapshotHash": report["snapshotHash"],
                    "state": "QUARANTINED",
                    "scannedBy": scanned_by,
                    "candidateFileCount": report["candidateFileCount"],
                    "eligibleFileCount": report["eligibleFileCount"],
                    "excludedFileCount": report["excludedFileCount"],
                    "blockingViolationCount": report["blockingViolationCount"],
                    "scannedAt": utc_now(),
                }
            )
            return self._remember("record_scan", idempotency_key, version)

    def list_source_files(self, version_id: UUID) -> list[dict[str, Any]]:
        with self._lock:
            if version_id not in self._source_versions:
                raise NotFoundError("source version not found")
            return deepcopy(sorted(self._source_files[version_id].values(), key=lambda item: item["path"]))

    def approve_version(self, version_id: UUID, request: dict[str, Any], idempotency_key: str) -> dict[str, Any]:
        from .source_registry import get_profile

        with self._lock:
            if repeated := self._repeat("approve_version", idempotency_key):
                return repeated
            version = self._source_versions.get(version_id)
            if not version:
                raise NotFoundError("source version not found")
            if version["state"] != "QUARANTINED":
                raise InvalidStateError("only quarantined source versions can be approved")
            if version["blockingViolationCount"] != 0 and not request.get("acceptQuarantineExclusions", False):
                raise InvalidStateError("blocking quarantine exclusions require explicit reviewer acceptance")
            expected_commit = request.get("expectedCommit")
            if expected_commit and expected_commit != version["commit"]:
                raise ConflictError("approval commit differs from scanned candidate")
            profile = get_profile(version["sourceProfileId"])
            if request["approvedBy"] != profile.initial_reviewer:
                raise InvalidBoundaryError("reviewer is not authorized for this source profile")
            version.update(
                {
                    "state": "APPROVED", "approvedAt": utc_now(), "approvedBy": request["approvedBy"],
                    "quarantineExclusionsAccepted": request.get("acceptQuarantineExclusions", False),
                }
            )
            return self._remember("approve_version", idempotency_key, version)

    def approve_source(self, source_id: UUID, request: dict[str, Any], idempotency_key: str) -> dict[str, Any]:
        with self._lock:
            if source_id not in self._sources:
                raise NotFoundError("source not found")
            version_id = self._latest_version(source_id)["sourceVersionId"]
        return self.approve_version(version_id, request, idempotency_key)

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
            if source_id not in self._sources:
                raise NotFoundError("source not found")
            source = self._latest_version(source_id)
            if source["state"] != "APPROVED":
                raise InvalidStateError("source must be approved before indexing")
            source["state"] = "INDEXING"
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

    def complete_job(self, job_id: UUID, request: dict[str, Any], idempotency_key: str) -> dict[str, Any]:
        with self._lock:
            if repeated := self._repeat("complete_job", idempotency_key):
                return repeated
            job = self._jobs.get(job_id)
            if not job:
                raise NotFoundError("job not found")
            if job["jobType"] != "INGESTION" or job["state"] not in {"PENDING", "RUNNING"}:
                raise InvalidStateError("job cannot complete indexing")
            version = self._source_versions[job["sourceVersionId"]]
            if version["state"] != "INDEXING":
                raise InvalidStateError("source version is not indexing")
            if request["succeeded"]:
                if request["indexedFileCount"] != version["eligibleFileCount"]:
                    raise ConflictError("partial indexing cannot activate a source version")
                for candidate in self._source_versions.values():
                    if candidate["sourceId"] == version["sourceId"] and candidate["state"] == "ACTIVE":
                        candidate["state"] = "WITHDRAWN"
                version.update({"state": "ACTIVE", "indexedFileCount": request["indexedFileCount"]})
                job.update({"state": "SUCCEEDED", "failureClass": None, "errorCode": None, "updatedAt": utc_now()})
            else:
                version["state"] = "APPROVED"
                job.update(
                    {"state": "FAILED", "failureClass": "TERMINAL", "errorCode": request["errorCode"], "updatedAt": utc_now()}
                )
            return self._remember("complete_job", idempotency_key, job)

    def withdraw_source(self, source_id: UUID, idempotency_key: str) -> dict[str, Any]:
        with self._lock:
            if repeated := self._repeat("withdraw_source", idempotency_key):
                return repeated
            source = self._sources.get(source_id)
            if not source:
                raise NotFoundError("source not found")
            version = self._latest_version(source_id)
            version["state"] = "WITHDRAWN"
            job_id = uuid4()
            value = {
                "jobId": job_id,
                "jobType": "DELETION",
                "sourceId": source_id,
                "sourceVersionId": version["sourceVersionId"],
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
