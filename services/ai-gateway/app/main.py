"""TechFlow AI Gateway Issue #41 FastAPI application."""

from __future__ import annotations

from contextlib import asynccontextmanager
import json
import logging
import re
import time
from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import BackgroundTasks, Depends, FastAPI, Header, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from . import __version__
from .config import ConfigurationError, Settings
from .models import (
    ApiMeta,
    CompatibilitySetCreateRequest,
    ComprehensiveQueryRequest,
    Envelope,
    EvaluationExecuteRequest,
    EvaluationRunCreateRequest,
    GroundedQueryRequest,
    IngestionCreateRequest,
    JobCompletionRequest,
    JobRunRequest,
    QueryRequest,
    SourceApprovalRequest,
    SourceCreateRequest,
    SourceDiscoveryRequest,
    SourceScanRequest,
)
from .evaluation import judge_case, load_golden_set
from .postgres_store import PostgresStore
from .embedding import EmbeddingsAdapter, build_embedding_adapter
from .provider import ComprehensiveResponsesRequest, ResponsesRequest, profile_payloads
from .responses import (
    ResponsesAdapter,
    ResponsesProviderError,
    build_responses_adapter,
    citation_payload,
    context_from_results,
    decide_generation,
    load_safety_identifier_salt,
    stable_safety_identifier,
    validate_grounded_result,
)
from .source_fetcher import FetchError, GitSnapshotFetcher, SnapshotFetcher
from .source_pipeline import SourcePipeline
from .source_registry import get_profile
from .store import InvalidBoundaryError, MemoryStore, Store, StoreError
from .artifacts import ArtifactStore
from .comprehensive import plan_query


CORRELATION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{7,127}$")
IDEMPOTENCY_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{15,127}$")
logger = logging.getLogger("techflow.ai_gateway")


def _json_log(event: str, **fields: object) -> None:
    safe = {"event": event, **fields}
    logger.info(json.dumps(safe, ensure_ascii=True, separators=(",", ":")))


MANUAL_REVIEW_ERROR_CODES = {"CONFLICT", "INVALID_STATE", "SOURCE_HEAD_MOVED"}


def _error(correlation_id: str, status_code: int, code: str) -> JSONResponse:
    if code in MANUAL_REVIEW_ERROR_CODES:
        failure_class = "MANUAL_REVIEW"
    elif status_code >= 500:
        failure_class = "RETRYABLE"
    else:
        failure_class = "TERMINAL"
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {"code": code, "failureClass": failure_class},
            "meta": {"correlationId": correlation_id, "apiVersion": "v1"},
        },
    )


def _envelope(data: Any, correlation_id: str) -> Envelope:
    return Envelope(data=data, meta=ApiMeta(correlationId=correlation_id))


def _model_data(model: Any) -> dict[str, Any]:
    return model.model_dump(by_alias=True, mode="json", exclude_none=False)


def _idempotency_key(idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None) -> str:
    if not idempotency_key or not IDEMPOTENCY_PATTERN.fullmatch(idempotency_key):
        raise InvalidBoundaryError("valid Idempotency-Key is required")
    return idempotency_key


def _correlation_id(request: Request) -> str:
    return request.state.correlation_id


def _build_store(settings: Settings) -> Store:
    if settings.store_backend == "postgres":
        return PostgresStore(settings)
    return MemoryStore()


def create_app(
    settings: Settings | None = None,
    store: Store | None = None,
    source_fetcher: SnapshotFetcher | None = None,
    embeddings_adapter: EmbeddingsAdapter | None = None,
    responses_adapter: ResponsesAdapter | None = None,
) -> FastAPI:
    runtime_settings = settings or Settings.from_env()
    runtime_settings.validate()
    runtime_store = store or _build_store(runtime_settings)
    runtime_embeddings = embeddings_adapter or build_embedding_adapter(runtime_settings)
    runtime_responses = responses_adapter or build_responses_adapter(runtime_settings)
    safety_identifier_salt = load_safety_identifier_salt(runtime_settings)
    source_pipeline = SourcePipeline(source_fetcher or GitSnapshotFetcher())
    artifact_store = ArtifactStore(
        runtime_settings.artifact_root,
        retention_hours=runtime_settings.artifact_retention_hours,
        max_bytes=runtime_settings.artifact_max_bytes,
        max_extracted_bytes=runtime_settings.artifact_max_extracted_bytes,
        max_archive_entries=runtime_settings.artifact_max_archive_entries,
        max_compression_ratio=runtime_settings.artifact_max_compression_ratio,
        max_log_evidence_chars=runtime_settings.artifact_max_log_evidence_chars,
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield
        runtime_store.close()

    application = FastAPI(
        title="TechFlow AI Gateway",
        version=__version__,
        description="TechFlow AI Gateway with grounded Responses generation and deterministic retrieval.",
        docs_url=None,
        redoc_url=None,
        lifespan=lifespan,
    )
    application.state.store = runtime_store
    application.state.settings = runtime_settings
    application.state.artifacts = artifact_store

    @application.middleware("http")
    async def boundary_middleware(request: Request, call_next):
        started = time.perf_counter()
        correlation_id = request.headers.get("X-Correlation-Id", "")
        if request.url.path.startswith("/v1") and not CORRELATION_PATTERN.fullmatch(correlation_id):
            return _error("missing", 400, "INVALID_CORRELATION_ID")
        request.state.correlation_id = correlation_id or "healthcheck"
        try:
            response = await call_next(request)
        except Exception as exc:
            _json_log(
                "request_failed",
                correlationId=request.state.correlation_id,
                method=request.method,
                path=request.url.path,
                status=500,
                errorType=type(exc).__name__,
            )
            return _error(request.state.correlation_id, 500, "INTERNAL_ERROR")
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        response.headers["X-Correlation-Id"] = request.state.correlation_id
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        _json_log(
            "request_completed",
            correlationId=request.state.correlation_id,
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            durationMs=duration_ms,
        )
        return response

    @application.exception_handler(StoreError)
    async def store_error_handler(request: Request, exc: StoreError):
        status_code = getattr(exc, "http_status", 500)
        code = getattr(exc, "code", "STORE_ERROR")
        return _error(getattr(request.state, "correlation_id", "missing"), status_code, code)

    @application.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        safe_fields = [".".join(str(item) for item in error["loc"] if item not in {"body"}) for error in exc.errors()]
        response = _error(getattr(request.state, "correlation_id", "missing"), 422, "VALIDATION_ERROR")
        payload = json.loads(response.body)
        payload["error"]["fields"] = safe_fields[:20]
        safe_headers = {
            key: value
            for key, value in response.headers.items()
            if key.lower() not in {"content-length", "content-type"}
        }
        return JSONResponse(status_code=422, content=payload, headers=safe_headers)

    @application.get("/healthz", response_model=Envelope, operation_id="getHealth")
    def health() -> Envelope | JSONResponse:
        health_data = runtime_store.health()
        health_data["version"] = __version__
        health_data["providerProfiles"] = profile_payloads()
        if health_data.get("database") != "ready" or health_data.get("vector") not in {"ready", "not-applicable"}:
            return JSONResponse(status_code=503, content=_envelope(health_data, "healthcheck").model_dump(by_alias=True, mode="json"))
        return _envelope(health_data, "healthcheck")

    @application.post("/v1/sources", response_model=Envelope, status_code=status.HTTP_201_CREATED, operation_id="createSource")
    def create_source(
        request: SourceCreateRequest,
        correlation_id: Annotated[str, Depends(_correlation_id)],
        idempotency_key: Annotated[str, Depends(_idempotency_key)],
    ) -> Envelope:
        return _envelope(runtime_store.create_source(_model_data(request), idempotency_key), correlation_id)

    @application.get("/v1/source-profiles", response_model=Envelope, operation_id="listSourceProfiles")
    def list_source_profiles(correlation_id: Annotated[str, Depends(_correlation_id)]) -> Envelope:
        return _envelope(runtime_store.list_source_profiles(), correlation_id)

    @application.get("/v1/source-mirrors", response_model=Envelope, operation_id="listSourceMirrors")
    def list_source_mirrors(correlation_id: Annotated[str, Depends(_correlation_id)]) -> Envelope:
        return _envelope(runtime_store.list_source_mirrors(), correlation_id)

    @application.post(
        "/v1/source-profiles/{sourceProfileId}/discoveries",
        response_model=Envelope,
        status_code=status.HTTP_201_CREATED,
        operation_id="discoverSourceCandidate",
    )
    def discover_source_candidate(
        sourceProfileId: str,
        request: SourceDiscoveryRequest,
        correlation_id: Annotated[str, Depends(_correlation_id)],
        idempotency_key: Annotated[str, Depends(_idempotency_key)],
    ) -> Envelope:
        profile = get_profile(sourceProfileId)
        started = time.perf_counter()
        try:
            commit = source_pipeline.discover(profile)
        except FetchError as exc:
            runtime_store.record_mirror_sync(
                profile.repository, None, False, exc.code, round((time.perf_counter() - started) * 1000)
            )
            raise
        runtime_store.record_mirror_sync(
            profile.repository, commit, True, None, round((time.perf_counter() - started) * 1000)
        )
        data = runtime_store.register_candidate(profile.profile_id, commit, request.detected_by, idempotency_key)
        return _envelope(data, correlation_id)

    @application.get("/v1/source-versions/{sourceVersionId}", response_model=Envelope, operation_id="getSourceVersion")
    def get_source_version(
        sourceVersionId: UUID, correlation_id: Annotated[str, Depends(_correlation_id)]
    ) -> Envelope:
        return _envelope(runtime_store.get_source_version(sourceVersionId), correlation_id)

    @application.post(
        "/v1/source-versions/{sourceVersionId}/scan",
        response_model=Envelope,
        operation_id="scanSourceVersion",
    )
    def scan_source_version(
        sourceVersionId: UUID,
        request: SourceScanRequest,
        correlation_id: Annotated[str, Depends(_correlation_id)],
        idempotency_key: Annotated[str, Depends(_idempotency_key)],
    ) -> Envelope:
        version = runtime_store.get_source_version(sourceVersionId)
        profile = get_profile(version["sourceProfileId"])
        report = source_pipeline.scan(profile, version["commit"])
        return _envelope(
            runtime_store.record_scan(sourceVersionId, report, request.scanned_by, idempotency_key), correlation_id
        )

    @application.get(
        "/v1/source-versions/{sourceVersionId}/files", response_model=Envelope, operation_id="listSourceVersionFiles"
    )
    def list_source_version_files(
        sourceVersionId: UUID, correlation_id: Annotated[str, Depends(_correlation_id)]
    ) -> Envelope:
        return _envelope(runtime_store.list_source_files(sourceVersionId), correlation_id)

    @application.post(
        "/v1/source-versions/{sourceVersionId}/approve", response_model=Envelope, operation_id="approveSourceVersion"
    )
    def approve_source_version(
        sourceVersionId: UUID,
        request: SourceApprovalRequest,
        correlation_id: Annotated[str, Depends(_correlation_id)],
        idempotency_key: Annotated[str, Depends(_idempotency_key)],
    ) -> Envelope:
        return _envelope(
            runtime_store.approve_version(sourceVersionId, _model_data(request), idempotency_key), correlation_id
        )

    @application.get("/v1/sources/{sourceId}", response_model=Envelope, operation_id="getSource")
    def get_source(sourceId: UUID, correlation_id: Annotated[str, Depends(_correlation_id)]) -> Envelope:
        return _envelope(runtime_store.get_source(sourceId), correlation_id)

    @application.post("/v1/compatibility-sets", response_model=Envelope, status_code=status.HTTP_201_CREATED, operation_id="createCompatibilitySet")
    def create_compatibility_set(
        request: CompatibilitySetCreateRequest,
        correlation_id: Annotated[str, Depends(_correlation_id)],
        idempotency_key: Annotated[str, Depends(_idempotency_key)],
    ) -> Envelope:
        return _envelope(runtime_store.create_compatibility_set(_model_data(request), idempotency_key), correlation_id)

    @application.post("/v1/sources/{sourceId}/approve", response_model=Envelope, operation_id="approveSource")
    def approve_source(
        sourceId: UUID,
        request: SourceApprovalRequest,
        correlation_id: Annotated[str, Depends(_correlation_id)],
        idempotency_key: Annotated[str, Depends(_idempotency_key)],
    ) -> Envelope:
        return _envelope(runtime_store.approve_source(sourceId, _model_data(request), idempotency_key), correlation_id)

    @application.post("/v1/sources/{sourceId}/ingestions", response_model=Envelope, status_code=status.HTTP_202_ACCEPTED, operation_id="createIngestion")
    def create_ingestion(
        sourceId: UUID,
        request: IngestionCreateRequest,
        correlation_id: Annotated[str, Depends(_correlation_id)],
        idempotency_key: Annotated[str, Depends(_idempotency_key)],
    ) -> Envelope:
        return _envelope(
            runtime_store.create_ingestion(sourceId, _model_data(request), idempotency_key, correlation_id),
            correlation_id,
        )

    @application.delete("/v1/sources/{sourceId}", response_model=Envelope, status_code=status.HTTP_202_ACCEPTED, operation_id="withdrawSource")
    def withdraw_source(
        sourceId: UUID,
        correlation_id: Annotated[str, Depends(_correlation_id)],
        idempotency_key: Annotated[str, Depends(_idempotency_key)],
    ) -> Envelope:
        return _envelope(runtime_store.withdraw_source(sourceId, idempotency_key, correlation_id), correlation_id)

    @application.get("/v1/jobs/{jobId}", response_model=Envelope, operation_id="getJob")
    def get_job(jobId: UUID, correlation_id: Annotated[str, Depends(_correlation_id)]) -> Envelope:
        return _envelope(runtime_store.get_job(jobId), correlation_id)

    @application.post("/v1/jobs/{jobId}/run", response_model=Envelope, operation_id="runIndexingJob")
    def run_job(
        jobId: UUID,
        request: JobRunRequest,
        correlation_id: Annotated[str, Depends(_correlation_id)],
        idempotency_key: Annotated[str, Depends(_idempotency_key)],
    ) -> Envelope:
        return _envelope(
            runtime_store.run_job(jobId, _model_data(request), idempotency_key, correlation_id,
                                  runtime_embeddings, runtime_settings.embedding_batch_size),
            correlation_id,
        )

    @application.post("/v1/jobs/{jobId}/complete", response_model=Envelope, operation_id="completeIngestionJob")
    def complete_ingestion_job(
        jobId: UUID,
        request: JobCompletionRequest,
        correlation_id: Annotated[str, Depends(_correlation_id)],
        idempotency_key: Annotated[str, Depends(_idempotency_key)],
    ) -> Envelope:
        return _envelope(runtime_store.complete_job(jobId, _model_data(request), idempotency_key), correlation_id)

    def _retrieve(request: QueryRequest, correlation_id: str) -> dict[str, Any]:
        result = runtime_embeddings.embed([request.question])
        return runtime_store.retrieve(_model_data(request), result, correlation_id)

    @application.post("/v1/rag/retrieve", response_model=Envelope, operation_id="retrieveRagContext")
    def retrieve_rag(request: QueryRequest, correlation_id: Annotated[str, Depends(_correlation_id)]) -> Envelope:
        return _envelope(_retrieve(request, correlation_id), correlation_id)

    def _query_grounded(request: GroundedQueryRequest, correlation_id: str) -> dict[str, Any]:
        scope = {
            "sourceProfileIds": request.source_profile_ids,
            "compatibilitySetId": request.compatibility_set_id,
        }
        retrieval = _retrieve(request, correlation_id)
        decision = decide_generation(
            retrieval["results"],
            compatibility_set_id=str(request.compatibility_set_id) if request.compatibility_set_id else None,
            source_profile_ids=request.source_profile_ids,
        )
        common = {
            "queryId": request.query_id,
            "scope": scope,
            "retrieval": {
                "resultCount": retrieval["resultCount"],
                "provider": retrieval["provider"],
                "providerCalled": retrieval["providerCalled"],
            },
            "retrievalProviderCalled": retrieval["providerCalled"],
        }
        if decision.state == "ABSTAINED":
            return {**common, "state": "ABSTAINED", "abstainReason": decision.abstain_reason,
                    "answer": None, "citations": [], "providerProfileId": None,
                    "generationProviderCalled": False}
        context = context_from_results(retrieval["results"], request.classification)
        provider_request = ResponsesRequest(
            query_id=str(request.query_id),
            question=request.question,
            profile_id=decision.profile_id or "",
            context=context,
            locale=request.locale,
            safety_identifier=stable_safety_identifier(request.actor_id, safety_identifier_salt),
        )
        try:
            generated = runtime_responses.generate(provider_request)
            runtime_store.record_response_call(request.query_id, generated, correlation_id)
            state, answer, abstain_reason, cited = validate_grounded_result(generated, context)
            return {**common, "state": state, "abstainReason": abstain_reason, "answer": answer,
                    "citations": [citation_payload(item) for item in cited],
                    "providerProfileId": generated.profile_id,
                    "generationProviderCalled": generated.provider == "openai"}
        except ResponsesProviderError as exc:
            runtime_store.record_response_failure(request.query_id, exc, correlation_id)
            return {**common, "state": "FAILED", "abstainReason": None, "answer": None,
                    "citations": [], "providerProfileId": exc.profile_id,
                    "generationProviderCalled": exc.provider_called,
                    "errorCode": exc.code, "failureClass": exc.failure_class}

    @application.post("/v1/rag/query", response_model=Envelope, operation_id="queryRag")
    def query_rag(request: GroundedQueryRequest, correlation_id: Annotated[str, Depends(_correlation_id)]) -> Envelope:
        return _envelope(_query_grounded(request, correlation_id), correlation_id)

    @application.post("/v1/artifacts", response_model=Envelope, status_code=status.HTTP_201_CREATED, operation_id="createArtifact")
    async def create_artifact(
        request: Request,
        correlation_id: Annotated[str, Depends(_correlation_id)],
        filename: Annotated[str, Header(alias="X-Artifact-Filename")],
        classification: Annotated[str, Header(alias="X-Artifact-Classification")] = "D0",
    ) -> Envelope:
        if classification != "D0":
            raise InvalidBoundaryError("only D0 artifacts are permitted")
        media_type = request.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        record = artifact_store.put(filename, media_type, await request.body())
        return _envelope(record.payload(), correlation_id)

    @application.get("/v1/artifacts/{artifactId}", response_model=Envelope, operation_id="getArtifact")
    def get_artifact(artifactId: UUID, correlation_id: Annotated[str, Depends(_correlation_id)]) -> Envelope:
        return _envelope(artifact_store.get(artifactId).payload(), correlation_id)

    @application.delete("/v1/artifacts/{artifactId}", response_model=Envelope, operation_id="deleteArtifact")
    def delete_artifact(
        artifactId: UUID,
        correlation_id: Annotated[str, Depends(_correlation_id)],
        idempotency_key: Annotated[str, Depends(_idempotency_key)],
    ) -> Envelope:
        return _envelope({"artifactId": artifactId, "deleted": artifact_store.delete(artifactId)}, correlation_id)

    def _query_comprehensive(request: ComprehensiveQueryRequest, correlation_id: str) -> dict[str, Any]:
        compatibility = runtime_store.resolve_compatibility_set(request.compatibility_set_id, request.product_version)
        explicit_profiles = request.source_profile_ids or (compatibility or {}).get("sourceProfileIds")
        plan = plan_query(request.question, explicit_profiles)
        if plan.state != "READY":
            return {"queryId": request.query_id, "state": "NEEDS_INFORMATION", "plan": plan.payload(),
                    "report": None, "citations": [], "generationProviderCalled": False}
        profiles = list(plan.profile_ids)
        if compatibility and not set(profiles).issubset(set(compatibility["sourceProfileIds"])):
            return {"queryId": request.query_id, "state": "NEEDS_INFORMATION", "plan": plan.payload(),
                    "questionsNeeded": ["선택한 영역을 모두 포함하는 승인된 Compatibility Set이 필요합니다."],
                    "report": None, "citations": [], "generationProviderCalled": False}
        if len(profiles) > 1 and not compatibility:
            return {"queryId": request.query_id, "state": "NEEDS_INFORMATION", "plan": plan.payload(),
                    "questionsNeeded": ["제품 버전 또는 승인된 compatibilitySetId를 지정하십시오."],
                    "report": None, "citations": [], "generationProviderCalled": False}
        scope = {"compatibilitySetId": compatibility["compatibilitySetId"] if compatibility else None,
                 "sourceProfileIds": None if compatibility else profiles}
        retrieval_request = QueryRequest(
            queryId=request.query_id, question=request.question,
            compatibilitySetId=scope["compatibilitySetId"], sourceProfileIds=scope["sourceProfileIds"],
            locale=request.locale, classification=request.classification,
        )
        retrieval = _retrieve(retrieval_request, correlation_id)
        context = context_from_results(retrieval["results"], request.classification)
        if not context:
            return {"queryId": request.query_id, "state": "ABSTAINED", "plan": plan.payload(),
                    "report": None, "citations": [], "abstainReason": "no-grounding", "generationProviderCalled": False}
        artifacts = tuple(artifact_store.evidence(artifact_id) for artifact_id in request.artifact_ids)
        provider_request = ComprehensiveResponsesRequest(
            query_id=str(request.query_id), question=request.question, context=context, artifacts=artifacts,
            locale=request.locale, safety_identifier=stable_safety_identifier(request.actor_id, safety_identifier_salt),
        )
        try:
            generated = runtime_responses.generate_comprehensive(provider_request)
            runtime_store.record_response_call(request.query_id, generated, correlation_id)
            cited = {item.chunk_id: item for item in context}
            citations = [citation_payload(cited[item]) for item in generated.citations_used if item in cited]
            return {"queryId": request.query_id, "state": generated.report["state"], "plan": plan.payload(),
                    "scope": scope, "report": generated.report, "citations": citations,
                    "generationProviderCalled": generated.provider == "openai", "providerProfileId": generated.profile_id}
        except ResponsesProviderError as exc:
            runtime_store.record_response_failure(request.query_id, exc, correlation_id)
            return {"queryId": request.query_id, "state": "FAILED", "plan": plan.payload(), "report": None,
                    "citations": [], "generationProviderCalled": exc.provider_called, "errorCode": exc.code,
                    "failureClass": exc.failure_class}

    @application.post("/v1/assist/query", response_model=Envelope, operation_id="queryAssist")
    def query_assist(request: ComprehensiveQueryRequest, correlation_id: Annotated[str, Depends(_correlation_id)]) -> Envelope:
        return _envelope(_query_comprehensive(request, correlation_id), correlation_id)

    @application.post("/v1/evaluations/runs", response_model=Envelope, status_code=status.HTTP_202_ACCEPTED, operation_id="createEvaluationRun")
    def create_evaluation_run(
        request: EvaluationRunCreateRequest,
        correlation_id: Annotated[str, Depends(_correlation_id)],
        idempotency_key: Annotated[str, Depends(_idempotency_key)],
    ) -> Envelope:
        return _envelope(
            runtime_store.create_evaluation_run(_model_data(request), idempotency_key, correlation_id),
            correlation_id,
        )

    @application.get("/v1/evaluations/runs/{runId}", response_model=Envelope, operation_id="getEvaluationRun")
    def get_evaluation_run(runId: UUID, correlation_id: Annotated[str, Depends(_correlation_id)]) -> Envelope:
        return _envelope(runtime_store.get_evaluation_run(runId), correlation_id)

    def _execute_golden_cases(run_id: UUID, cases: list[dict[str, Any]], actor_id: str) -> None:
        try:
            for index, case in enumerate(cases, 1):
                case_correlation_id = f"eval-{str(run_id)[:12]}-{index:03d}"
                started = time.perf_counter()
                result = _query_grounded(
                    GroundedQueryRequest(
                        queryId=uuid4(),
                        question=case["question"],
                        actorId=actor_id,
                        sourceProfileIds=case["sourceProfileIds"],
                        classification="D0",
                        locale=case["locale"],
                    ),
                    case_correlation_id,
                )
                latency_ms = round((time.perf_counter() - started) * 1000)
                runtime_store.record_evaluation_result(
                    run_id, case, result, judge_case(case, result).payload(), latency_ms
                )
            runtime_store.finish_evaluation_run(run_id)
        except Exception as exc:
            _json_log("evaluation_failed", runId=str(run_id), errorType=type(exc).__name__)
            try:
                runtime_store.finish_evaluation_run(run_id, failed=True)
            except Exception:
                _json_log("evaluation_failure_record_failed", runId=str(run_id))

    @application.post(
        "/v1/evaluations/runs/{runId}/execute",
        response_model=Envelope,
        status_code=status.HTTP_202_ACCEPTED,
        operation_id="executeEvaluationRun",
    )
    def execute_evaluation_run(
        runId: UUID,
        request: EvaluationExecuteRequest,
        background_tasks: BackgroundTasks,
        correlation_id: Annotated[str, Depends(_correlation_id)],
    ) -> Envelope:
        run = runtime_store.get_evaluation_run(runId)
        profiles = set(run.get("sourceProfileIds") or [])
        if not profiles:
            raise InvalidBoundaryError("Golden Set execution requires sourceProfileIds scope")
        golden = load_golden_set()
        cases = [case for case in golden["cases"] if set(case["sourceProfileIds"]).issubset(profiles)]
        if not cases:
            raise InvalidBoundaryError("evaluation scope selects no Golden Set cases")
        runtime_store.start_evaluation_run(runId, len(cases))
        background_tasks.add_task(_execute_golden_cases, runId, cases, request.requested_by)
        return _envelope(
            {"runId": runId, "caseSetId": request.case_set_id, "state": "RUNNING", "totalCases": len(cases)},
            correlation_id,
        )

    @application.get(
        "/v1/evaluations/runs/{runId}/results",
        response_model=Envelope,
        operation_id="listEvaluationResults",
    )
    def list_evaluation_results(
        runId: UUID, correlation_id: Annotated[str, Depends(_correlation_id)]
    ) -> Envelope:
        return _envelope(runtime_store.list_evaluation_results(runId), correlation_id)

    return application


try:
    app = create_app()
except ConfigurationError:
    raise
