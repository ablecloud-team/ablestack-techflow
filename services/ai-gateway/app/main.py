"""TechFlow AI Gateway Issue #41 FastAPI application."""

from __future__ import annotations

from contextlib import asynccontextmanager
import json
import logging
import re
import time
from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, FastAPI, Header, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from . import __version__
from .config import ConfigurationError, Settings
from .models import (
    ApiMeta,
    CompatibilitySetCreateRequest,
    Envelope,
    EvaluationRunCreateRequest,
    IngestionCreateRequest,
    QueryRequest,
    SourceApprovalRequest,
    SourceCreateRequest,
)
from .postgres_store import PostgresStore
from .provider import profile_payloads
from .store import InvalidBoundaryError, MemoryStore, Store, StoreError


CORRELATION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{7,127}$")
IDEMPOTENCY_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{15,127}$")
logger = logging.getLogger("techflow.ai_gateway")


def _json_log(event: str, **fields: object) -> None:
    safe = {"event": event, **fields}
    logger.info(json.dumps(safe, ensure_ascii=True, separators=(",", ":")))


def _error(correlation_id: str, status_code: int, code: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {"code": code, "failureClass": "TERMINAL" if status_code < 500 else "RETRYABLE"},
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


def create_app(settings: Settings | None = None, store: Store | None = None) -> FastAPI:
    runtime_settings = settings or Settings.from_env()
    runtime_settings.validate()
    runtime_store = store or _build_store(runtime_settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield
        runtime_store.close()

    application = FastAPI(
        title="TechFlow AI Gateway",
        version=__version__,
        description="Issue #41 API, database, provider profile, and mock adapter foundation.",
        docs_url=None,
        redoc_url=None,
        lifespan=lifespan,
    )
    application.state.store = runtime_store
    application.state.settings = runtime_settings

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
        return JSONResponse(status_code=422, content=payload, headers=dict(response.headers))

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
        return _envelope(runtime_store.create_ingestion(sourceId, _model_data(request), idempotency_key), correlation_id)

    @application.delete("/v1/sources/{sourceId}", response_model=Envelope, status_code=status.HTTP_202_ACCEPTED, operation_id="withdrawSource")
    def withdraw_source(
        sourceId: UUID,
        correlation_id: Annotated[str, Depends(_correlation_id)],
        idempotency_key: Annotated[str, Depends(_idempotency_key)],
    ) -> Envelope:
        return _envelope(runtime_store.withdraw_source(sourceId, idempotency_key), correlation_id)

    @application.get("/v1/jobs/{jobId}", response_model=Envelope, operation_id="getJob")
    def get_job(jobId: UUID, correlation_id: Annotated[str, Depends(_correlation_id)]) -> Envelope:
        return _envelope(runtime_store.get_job(jobId), correlation_id)

    @application.post("/v1/rag/query", response_model=Envelope, operation_id="queryRag")
    def query_rag(request: QueryRequest, correlation_id: Annotated[str, Depends(_correlation_id)]) -> Envelope:
        scope = {
            "sourceProfileIds": request.source_profile_ids,
            "compatibilitySetId": request.compatibility_set_id,
        }
        return _envelope(
            {
                "queryId": request.query_id,
                "state": "ABSTAINED",
                "abstainReason": "RETRIEVAL_NOT_IMPLEMENTED_UNTIL_ISSUE_43",
                "answer": None,
                "citations": [],
                "scope": scope,
                "providerCalled": False,
            },
            correlation_id,
        )

    @application.post("/v1/evaluations/runs", response_model=Envelope, status_code=status.HTTP_202_ACCEPTED, operation_id="createEvaluationRun")
    def create_evaluation_run(
        request: EvaluationRunCreateRequest,
        correlation_id: Annotated[str, Depends(_correlation_id)],
        idempotency_key: Annotated[str, Depends(_idempotency_key)],
    ) -> Envelope:
        return _envelope(runtime_store.create_evaluation_run(_model_data(request), idempotency_key), correlation_id)

    @application.get("/v1/evaluations/runs/{runId}", response_model=Envelope, operation_id="getEvaluationRun")
    def get_evaluation_run(runId: UUID, correlation_id: Annotated[str, Depends(_correlation_id)]) -> Envelope:
        return _envelope(runtime_store.get_evaluation_run(runId), correlation_id)

    return application


try:
    app = create_app()
except ConfigurationError:
    raise
