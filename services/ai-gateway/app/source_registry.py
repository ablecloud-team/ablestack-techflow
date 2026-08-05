"""Immutable ABLESTACK source profile registry for Issue #42."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Final

from .store import InvalidBoundaryError, NotFoundError


@dataclass(frozen=True)
class SourceProfile:
    profile_id: str
    owner: str
    repository: str
    branch: str
    source_kind: str
    classification: str
    license_spdx: str
    retention_policy: str
    initial_reviewer: str
    docs_root: str | None = None

    def payload(self) -> dict[str, object]:
        value = asdict(self)
        return {
            "sourceProfileId": value["profile_id"],
            "owner": value["owner"],
            "repository": value["repository"],
            "branch": value["branch"],
            "sourceKind": value["source_kind"],
            "classification": value["classification"],
            "licenseSpdx": value["license_spdx"],
            "retentionPolicy": value["retention_policy"],
            "initialReviewer": value["initial_reviewer"],
            "docsRoot": value["docs_root"],
        }


_COMMON = {
    "owner": "ablecloud-team",
    "classification": "D0",
    "retention_policy": "ACTIVE_PLUS_7D_DELETION_SLA",
    "initial_reviewer": "dhslove",
}

SOURCE_PROFILES: Final[dict[str, SourceProfile]] = {
    "SHARED_DOCS": SourceProfile(
        profile_id="SHARED_DOCS", repository="ablecloud-team/ablestack-docs", branch="master",
        source_kind="DOCUMENTATION", license_spdx="NOASSERTION", docs_root="docs/", **_COMMON,
    ),
    "CLOUD_MAIN": SourceProfile(
        profile_id="CLOUD_MAIN", repository="ablecloud-team/ablestack-cloud", branch="main",
        source_kind="SOURCE_CODE", license_spdx="Apache-2.0", **_COMMON,
    ),
    "CLOUD_DIPLO": SourceProfile(
        profile_id="CLOUD_DIPLO", repository="ablecloud-team/ablestack-cloud", branch="ablestack-diplo",
        source_kind="SOURCE_CODE", license_spdx="Apache-2.0", **_COMMON,
    ),
    "CLOUD_EUROPA": SourceProfile(
        profile_id="CLOUD_EUROPA", repository="ablecloud-team/ablestack-cloud", branch="ablestack-europa",
        source_kind="SOURCE_CODE", license_spdx="Apache-2.0", **_COMMON,
    ),
    "WALL_MAIN": SourceProfile(
        profile_id="WALL_MAIN", repository="ablecloud-team/ablestack-wall", branch="main",
        source_kind="SOURCE_CODE", license_spdx="AGPL-3.0", **_COMMON,
    ),
    "COCKPIT_DIPLO": SourceProfile(
        profile_id="COCKPIT_DIPLO", repository="ablecloud-team/ablestack-cockpit-plugin", branch="ablestack-diplo",
        source_kind="SOURCE_CODE", license_spdx="NOASSERTION", **_COMMON,
    ),
    "GENIE_MASTER": SourceProfile(
        profile_id="GENIE_MASTER", repository="ablecloud-team/ablestack-genie", branch="master",
        source_kind="SOURCE_CODE", license_spdx="NOASSERTION", **_COMMON,
    ),
    "KICKSTART_MASTER": SourceProfile(
        profile_id="KICKSTART_MASTER", repository="ablecloud-team/ablestack-kickstart", branch="master",
        source_kind="SOURCE_CODE", license_spdx="NOASSERTION", **_COMMON,
    ),
    "QEMU_EXEC_TOOLS_MAIN": SourceProfile(
        profile_id="QEMU_EXEC_TOOLS_MAIN", repository="ablecloud-team/ablestack-qemu-exec-tools", branch="main",
        source_kind="SOURCE_CODE", license_spdx="NOASSERTION", **_COMMON,
    ),
}


def get_profile(profile_id: str) -> SourceProfile:
    try:
        return SOURCE_PROFILES[profile_id]
    except KeyError as exc:
        raise NotFoundError("source profile is not allowlisted") from exc


def validate_candidate_contract(request: dict[str, object]) -> SourceProfile:
    profile = get_profile(str(request["sourceProfileId"]))
    expected = {
        "repository": profile.repository,
        "branch": profile.branch,
        "sourceKind": profile.source_kind,
        "classification": profile.classification,
    }
    if any(request.get(key) != value for key, value in expected.items()):
        raise InvalidBoundaryError("candidate does not match immutable source profile")
    supplied_license = request.get("licenseSpdx")
    if supplied_license not in {None, profile.license_spdx}:
        raise InvalidBoundaryError("license metadata does not match source profile")
    return profile


def list_profiles() -> list[dict[str, object]]:
    return [SOURCE_PROFILES[key].payload() for key in SOURCE_PROFILES]
