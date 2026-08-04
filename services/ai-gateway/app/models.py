"""HTTP request and response contracts for TechFlow AI Gateway v1."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator


SafeId = Annotated[str, StringConstraints(pattern=r"^[A-Z][A-Z0-9_]{2,63}$")]
CommitSha = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]
RepositoryName = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")]


class SourceKind(StrEnum):
    DOCUMENTATION = "DOCUMENTATION"
    SOURCE_CODE = "SOURCE_CODE"


class SourceState(StrEnum):
    QUARANTINED = "QUARANTINED"
    ACTIVE = "ACTIVE"
    WITHDRAWN = "WITHDRAWN"


class JobState(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class AnswerState(StrEnum):
    ANSWERED = "ANSWERED"
    ABSTAINED = "ABSTAINED"
    FAILED = "FAILED"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class ApiMeta(StrictModel):
    correlation_id: str = Field(alias="correlationId")
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), alias="generatedAt")
    api_version: str = Field(default="v1", alias="apiVersion")


class Envelope(StrictModel):
    data: Any
    meta: ApiMeta


class SourceCreateRequest(StrictModel):
    source_profile_id: SafeId = Field(alias="sourceProfileId")
    repository: RepositoryName
    branch: Annotated[str, StringConstraints(min_length=1, max_length=128)]
    commit: CommitSha
    source_kind: SourceKind = Field(alias="sourceKind")
    classification: Literal["D0"] = "D0"
    license_spdx: Annotated[str, StringConstraints(min_length=1, max_length=64)] | None = Field(default=None, alias="licenseSpdx")


class SourceApprovalRequest(StrictModel):
    approved_by: Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_.:@-]{3,128}$")] = Field(alias="approvedBy")
    decision_note: Annotated[str, StringConstraints(max_length=500)] | None = Field(default=None, alias="decisionNote")


class CompatibilityMember(StrictModel):
    source_version_id: UUID = Field(alias="sourceVersionId")
    required: bool = True


class CompatibilitySetCreateRequest(StrictModel):
    name: Annotated[str, StringConstraints(min_length=3, max_length=128)]
    product: Literal["ABLESTACK"] = "ABLESTACK"
    product_version: Annotated[str, StringConstraints(min_length=1, max_length=64)] = Field(alias="productVersion")
    members: list[CompatibilityMember] = Field(min_length=1, max_length=16)

    @model_validator(mode="after")
    def unique_members(self) -> "CompatibilitySetCreateRequest":
        ids = [member.source_version_id for member in self.members]
        if len(ids) != len(set(ids)):
            raise ValueError("members must be unique")
        return self


class IngestionCreateRequest(StrictModel):
    requested_by: Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_.:@-]{3,128}$")] = Field(alias="requestedBy")


class QueryRequest(StrictModel):
    query_id: UUID = Field(alias="queryId")
    question: Annotated[str, StringConstraints(min_length=3, max_length=4000)]
    source_profile_ids: list[SafeId] | None = Field(default=None, min_length=1, max_length=9, alias="sourceProfileIds")
    compatibility_set_id: UUID | None = Field(default=None, alias="compatibilitySetId")
    locale: Literal["ko-KR", "en-US"] = "ko-KR"
    classification: Literal["D0"] = "D0"

    @model_validator(mode="after")
    def exactly_one_scope(self) -> "QueryRequest":
        if bool(self.source_profile_ids) == bool(self.compatibility_set_id):
            raise ValueError("exactly one query scope is required")
        return self


class EvaluationRunCreateRequest(StrictModel):
    name: Annotated[str, StringConstraints(min_length=3, max_length=128)]
    source_profile_ids: list[SafeId] | None = Field(default=None, min_length=1, max_length=9, alias="sourceProfileIds")
    compatibility_set_id: UUID | None = Field(default=None, alias="compatibilitySetId")
    provider_profile_id: Literal["OPENAI_RAG_DEFAULT_V1", "OPENAI_RAG_ESCALATION_V1"] = Field(alias="providerProfileId")
    requested_by: Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_.:@-]{3,128}$")] = Field(alias="requestedBy")

    @model_validator(mode="after")
    def exactly_one_scope(self) -> "EvaluationRunCreateRequest":
        if bool(self.source_profile_ids) == bool(self.compatibility_set_id):
            raise ValueError("exactly one evaluation scope is required")
        return self
