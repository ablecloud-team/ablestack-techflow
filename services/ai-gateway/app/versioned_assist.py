"""ABLESTACK Diplo-current and Europa-preview evidence policy."""

from __future__ import annotations

import re
from typing import Any, Iterable


CURRENT_SOURCE_PROFILES: tuple[str, ...] = (
    "SHARED_DOCS",
    "CLOUD_DIPLO",
    "WALL_MAIN",
    "COCKPIT_DIPLO",
    "GENIE_MASTER",
    "KICKSTART_MASTER",
    "QEMU_EXEC_TOOLS_MAIN",
)
PREVIEW_SOURCE_PROFILE = "CLOUD_EUROPA"
INTERNAL_REFERENCE_ONLY_PROFILE = "CLOUD_MAIN"
VERSIONED_SOURCE_PROFILES = CURRENT_SOURCE_PROFILES + (PREVIEW_SOURCE_PROFILE,)

SOURCE_ROLES = {
    "SHARED_DOCS": "CURRENT_DOCUMENTATION",
    "CLOUD_DIPLO": "CURRENT_RELEASED_CLOUD",
    "WALL_MAIN": "CURRENT_RELATED_PRODUCT",
    "COCKPIT_DIPLO": "CURRENT_RELATED_PRODUCT",
    "GENIE_MASTER": "CURRENT_RELATED_PRODUCT",
    "KICKSTART_MASTER": "CURRENT_RELATED_PRODUCT",
    "QEMU_EXEC_TOOLS_MAIN": "CURRENT_RELATED_PRODUCT",
    "CLOUD_EUROPA": "UNRELEASED_PREVIEW_CLOUD",
}


def versioned_plan(question: str) -> dict[str, object]:
    return {
        "state": "READY",
        "domains": ["ABLESTACK_PRODUCT"],
        "sourceProfileIds": list(VERSIONED_SOURCE_PROFILES),
        "subquestions": [
            "공개 문서와 Diplo 현재 출시 코드에서 현재 동작과 원인을 확인한다.",
            "Wall, Cockpit, Genie, Kickstart, QEMU 도구에서 연관 근거를 확인한다.",
            "Europa 미출시 코드에서 동일 문제의 개선 여부만 별도로 확인한다.",
        ],
        "questionsNeeded": [],
        "question": question,
    }


STOP_WORDS = {
    "ablestack", "diplo", "europa", "관련", "변경", "진행", "주요", "필드", "무엇", "알려줘", "알려주세요",
    "현재", "제품", "기준", "코드", "검토", "원인", "조치",
}


def _query_terms(question: str) -> set[str]:
    identifiers = {
        item.casefold() for item in re.findall(r"[A-Za-z][A-Za-z0-9_]{5,}", question)
        if item.casefold() not in {"ablestack", "diplo", "europa"}
    }
    if identifiers:
        return identifiers
    terms = set(re.findall(r"[A-Za-z][A-Za-z0-9_]{3,}|[가-힣]{2,}", question.casefold()))
    return {item for item in terms if item not in STOP_WORDS}


def relevant_results(question: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    terms = _query_terms(question)
    if not terms:
        return []
    relevant = []
    for item in rows:
        searchable = f"{item.get('symbol') or ''}\n{item.get('path') or ''}\n{item.get('content') or ''}".casefold()
        if any(term in searchable for term in terms):
            relevant.append(item)
    return relevant


def coverage_payload(question: str, results_by_profile: dict[str, list[dict[str, Any]]]) -> list[dict[str, object]]:
    relevant_by_profile = {key: relevant_results(question, value) for key, value in results_by_profile.items()}
    return [
        {
            "sourceProfileId": profile_id,
            "role": SOURCE_ROLES[profile_id],
            "state": "EVIDENCE_FOUND" if relevant_by_profile.get(profile_id) else "NO_RELEVANT_EVIDENCE",
            "evidenceCount": len(relevant_by_profile.get(profile_id) or ()),
        }
        for profile_id in VERSIONED_SOURCE_PROFILES
    ]


def select_context_results(question: str, results_by_profile: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """Keep every source reviewed while bounding a provider request to twenty chunks."""
    selected: list[dict[str, Any]] = []
    for profile_id in VERSIONED_SOURCE_PROFILES:
        limit = 2 if profile_id in {"SHARED_DOCS", "CLOUD_DIPLO", "CLOUD_EUROPA"} else 1
        selected.extend(relevant_results(question, results_by_profile.get(profile_id) or [])[:limit])
    return selected[:20]


def evidence_ledger(result: dict[str, Any]) -> dict[str, object]:
    report = result.get("report") or {}
    return {
        "policy": "DIPLO_CURRENT_EUROPA_PREVIEW_V1",
        "coverage": result.get("coverage") or [],
        "currentAssessment": report.get("currentAssessment"),
        "previewAssessment": report.get("previewAssessment"),
        "previewGuidance": report.get("previewGuidance"),
        "citations": result.get("citations") or [],
    }


def _projection_replacements(citations: Iterable[dict[str, Any]]) -> set[str]:
    values: set[str] = set()
    for item in citations:
        for key in ("repository", "branch", "commit", "path", "citationId", "chunkId", "sourceProfileId"):
            value = str(item.get(key) or "").strip()
            if value:
                values.add(value)
    values.update(VERSIONED_SOURCE_PROFILES)
    values.update({"CLOUD_MAIN", "ablecloud-team"})
    return values


def sanitize_public_text(value: object, citations: Iterable[dict[str, Any]] = ()) -> str:
    text = str(value or "").strip()
    for secret in sorted(_projection_replacements(citations), key=len, reverse=True):
        text = text.replace(secret, "제품 내부 구현")
    text = re.sub(r"(?:https?://)?(?:www\.)?github\.com/\S+", "제품 내부 근거", text, flags=re.IGNORECASE)
    text = re.sub(r"\b[0-9a-f]{40}\b", "제품 버전", text, flags=re.IGNORECASE)
    text = re.sub(r"(?:[\w.-]+/){2,}[\w.@-]+(?::\d+(?:-\d+)?)?", "제품 내부 경로", text)
    text = re.sub(r"\b(?:citation|chunk|evidence)[-_]?[A-Za-z0-9-]+\b", "내부 근거", text, flags=re.IGNORECASE)
    return re.sub(r"[ \t]+", " ", text).strip()


def format_public_answer(result: dict[str, Any]) -> str | None:
    if result.get("state") != "ANSWERED" or not result.get("report"):
        return None
    report = result["report"]
    citations = result.get("citations") or []
    lines = ["## ABLESTACK 트러블슈팅 가이드"]

    symptom_rows = [report.get("summary"), *(report.get("observedFacts") or [])]
    sections = (
        ("증상", symptom_rows, "확인된 증상 정보가 없습니다."),
        ("원인", report.get("diagnoses") or [], "현재 근거에서 확정된 원인은 없습니다."),
        ("해결 방법", report.get("recommendedActions") or [], "추가 진단 정보를 확보한 뒤 해결 방법을 결정해야 합니다."),
    )
    for heading, rows, empty_message in sections:
        values: list[str] = []
        for row in rows:
            raw = row if isinstance(row, str) else row.get("text") or row.get("title") or row.get("action") or ""
            clean = sanitize_public_text(raw, citations)
            if clean and clean not in values:
                values.append(clean)
        lines.extend(["", f"### {heading}"])
        lines.extend(f"- {value}" for value in values or [empty_message])
    current = report.get("currentAssessment")
    if current:
        labels = {
            "CURRENT_NORMAL": "현재 출시 버전에서 정상 동작으로 판단됩니다.",
            "CURRENT_CONFIG_ERROR": "현재 출시 버전의 설정 또는 환경 문제 가능성이 높습니다.",
            "CURRENT_DEFECT": "현재 출시 버전의 제품 결함 가능성이 확인됩니다.",
            "INSUFFICIENT_EVIDENCE": "현재 정보만으로는 출시 버전의 상태를 확정하기 어렵습니다.",
        }
        current_label = labels.get(current, sanitize_public_text(current, citations))
    preview = report.get("previewAssessment")
    guidance = sanitize_public_text(report.get("previewGuidance"), citations)
    preview_label = "이번 사례에서 차기 버전 비교는 적용 대상이 아닙니다."
    if preview and preview != "NOT_APPLICABLE":
        labels = {
            "PREVIEW_IMPROVED": "차기 버전 코드에서 관련 개선이 진행 중인 정황이 확인됩니다.",
            "PREVIEW_PARTIAL": "차기 버전 코드에 일부 관련 개선이 있으나 완전한 해결 여부는 추가 검증이 필요합니다.",
            "PREVIEW_NOT_FOUND": "차기 버전 코드에서 직접 대응하는 개선을 확인하지 못해 제품 보완 검토가 필요합니다.",
            "PREVIEW_INSUFFICIENT": "차기 버전 개선 여부를 판단할 근거가 충분하지 않습니다.",
        }
        preview_label = labels.get(preview, sanitize_public_text(preview, citations))

    considerations: list[str] = []
    for row in report.get("unknowns") or []:
        clean = sanitize_public_text(row, citations)
        if clean and clean not in considerations:
            considerations.append(clean)
    if guidance and guidance not in considerations:
        considerations.append(guidance)
    lines.extend(["", "### 추가 고려사항"])
    lines.extend(f"- {value}" for value in considerations or ["별도의 추가 고려사항은 확인되지 않았습니다."])

    lines.extend(["", "### 적용 버전"])
    if current:
        lines.append(f"- 현재 적용 기준: ABLESTACK Cloud Diplo(현재 출시판) - {current_label}")
    else:
        lines.append("- 현재 적용 기준: ABLESTACK Cloud Diplo(현재 출시판) - 판정 정보가 없습니다.")
    lines.append(f"- 차기 참고 기준: ABLESTACK Cloud Europa(미출시 Preview) - {preview_label}")
    lines.extend(["", "> 이 답변은 ABLESTACK TechFlow가 제품 자료와 구현을 종합 검토한 뒤 담당자 승인을 거쳐 제공합니다."])
    return "\n".join(line for line in lines if line is not None).strip()


def projection_is_safe(text: str) -> bool:
    forbidden = (
        r"github\.com/", r"\b[0-9a-f]{40}\b", r"CLOUD_(?:DIPLO|EUROPA|MAIN)",
        r"ablecloud-team/", r"#L\d+", r"(?:\.java|\.py|\.ts|\.md):\d+",
    )
    return not any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in forbidden)
