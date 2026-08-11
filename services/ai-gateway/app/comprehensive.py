"""Deterministic ABLESTACK planner and compatibility gate for Assist."""

from __future__ import annotations

from dataclasses import dataclass
import re


DOMAIN_RULES: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...] = (
    ("CLOUD", ("cloud", "cloudstack", "가상머신", "vm", "볼륨", "네트워크", "호스트"), ("CLOUD_MAIN", "CLOUD_DIPLO", "CLOUD_EUROPA")),
    ("WALL", ("wall", "ceph", "스토리지", "rbd"), ("WALL_MAIN",)),
    ("COCKPIT", ("cockpit", "대시보드", "웹 콘솔"), ("COCKPIT_DIPLO",)),
    ("GENIE", ("genie", "설치", "클러스터 구성"), ("GENIE_MASTER",)),
    ("KICKSTART", ("kickstart", "pxe", "무인 설치"), ("KICKSTART_MASTER",)),
    ("MIGRATION", ("qemu", "v2k", "n2k", "마이그레이션"), ("QEMU_EXEC_TOOLS_MAIN",)),
    ("DOCS", ("매뉴얼", "문서", "가이드"), ("SHARED_DOCS",)),
)


@dataclass(frozen=True)
class QueryPlan:
    state: str
    domains: tuple[str, ...]
    profile_ids: tuple[str, ...]
    subquestions: tuple[str, ...]
    questions_needed: tuple[str, ...] = ()

    def payload(self) -> dict[str, object]:
        return {"state": self.state, "domains": list(self.domains), "sourceProfileIds": list(self.profile_ids),
                "subquestions": list(self.subquestions), "questionsNeeded": list(self.questions_needed)}


def plan_query(question: str, explicit_profiles: list[str] | None = None) -> QueryPlan:
    if explicit_profiles:
        profiles = tuple(dict.fromkeys(explicit_profiles))
        domains = tuple(rule[0] for rule in DOMAIN_RULES if any(profile in rule[2] for profile in profiles))
        return QueryPlan("READY", domains or ("EXPLICIT",), profiles, tuple(f"{domain} 근거를 확인한다." for domain in domains or ("EXPLICIT",)))
    normalized = question.casefold()
    selected = [rule for rule in DOMAIN_RULES if any(re.search(rf"(?<![a-z0-9]){re.escape(keyword)}(?![a-z0-9])", normalized) if keyword.isascii() else keyword in normalized for keyword in rule[1])]
    if not selected:
        return QueryPlan("NEEDS_INFORMATION", (), (), (), ("어떤 ABLESTACK 구성요소 또는 기능에 관한 질문인지 알려주십시오.",))
    domains = tuple(rule[0] for rule in selected)
    profiles: list[str] = []
    for domain, _, candidates in selected:
        if domain == "CLOUD":
            branch_map = {"europa": "CLOUD_EUROPA", "diplo": "CLOUD_DIPLO", "main": "CLOUD_MAIN"}
            matches = [profile for key, profile in branch_map.items() if key in normalized]
            if len(matches) != 1:
                return QueryPlan("NEEDS_INFORMATION", domains, (), (), ("ablestack-cloud 대상 브랜치(main, ablestack-diplo, ablestack-europa)를 지정하십시오.",))
            profiles.extend(matches)
        else:
            profiles.extend(candidates)
    return QueryPlan("READY", domains, tuple(dict.fromkeys(profiles)), tuple(f"{domain} 영역에서 질문의 근거와 실행 경계를 확인한다." for domain in domains))
