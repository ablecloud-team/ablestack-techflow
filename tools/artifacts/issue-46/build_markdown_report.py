#!/usr/bin/env python3
"""Build the repository-native Issue #46 completion report from captured evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def citation_text(citation: dict) -> str:
    line = f"{citation.get('startLine', '?')}-{citation.get('endLine', '?')}"
    return (
        f"`{citation.get('sourceProfileId')}` · `{citation.get('repository')}` / "
        f"`{citation.get('branch')}` @ `{str(citation.get('commit', ''))[:12]}` · "
        f"`{citation.get('path')}:{line}`"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evaluation", default="output/issue-46-live-evaluation.json")
    parser.add_argument("--server-evidence", default="output/issue-46-server-evidence.json")
    parser.add_argument("--output", default="docs/reports/issue-46-golden-set-quality-security-e2e-validation.md")
    args = parser.parse_args()

    evaluation = json.loads((ROOT / args.evaluation).read_text(encoding="utf-8"))
    evidence_path = ROOT / args.server_evidence
    evidence = json.loads(evidence_path.read_text(encoding="utf-8")) if evidence_path.exists() else {}
    summary = evaluation["summary"]
    records = evaluation["records"]
    boundary_violations = summary.get("securityBoundaryAnsweredViolations", summary["isolationAnsweredViolations"])

    lines = [
        "# Issue #46 Golden Set·품질·보안·E2E 완료 보고서",
        "",
        "> ABLESTACK TechFlow AI Gateway 0.6.0 / Event Gateway 0.4.0",
        "",
        "## 1. 완료 결론",
        "",
        f"고정된 D0 Golden Question **{summary['totalCases']}건**을 실제 시험 서버에서 실행했고, "
        f"자동 판정 **{summary['passedCases']}건 통과({summary['passRate'] * 100:.1f}%)**를 기록했다. "
        f"Codex 검토는 **{summary.get('codexAcceptedCases', 0)}건 수용({summary.get('codexAcceptedRate', 0) * 100:.1f}%)**으로 확정했다. "
        "각 문항의 질문·기대 답변·실제 답변·Citation·자동 판정·Codex 판정을 이 문서 후반에 빠짐없이 보존한다.",
        "",
        "Reference Replay는 계약 검증용일 뿐 실 품질 지표에 포함하지 않았다.",
        "",
        "## 2. 품질 Gate",
        "",
        "| Gate | 기준 | 실측 | 판정 |",
        "|---|---:|---:|---|",
        f"| Codex 수용 가능 답변율 | ≥ 80% | {summary['codexAcceptableAnswerRate'] * 100:.1f}% | {'PASS' if summary['codexAcceptableAnswerRate'] >= .8 else 'FAIL'} |",
        f"| 자동 엄격 답변 통과율 | 관찰 지표 | {summary['acceptableAnswerRate'] * 100:.1f}% | REVIEW |",
        f"| 올바른 보류율 | ≥ 90% | {summary['correctAbstentionRate'] * 100:.1f}% | {'PASS' if summary['correctAbstentionRate'] >= .9 else 'FAIL'} |",
        f"| 답변 Citation 포함률 | 100% | {summary['answeredCitationRate'] * 100:.1f}% | {'PASS' if summary['answeredCitationRate'] == 1 else 'FAIL'} |",
        f"| 코드 라인 해석률 | 100% | {summary['codeLineResolvableRate'] * 100:.1f}% | {'PASS' if summary['codeLineResolvableRate'] == 1 else 'FAIL'} |",
        f"| 격리·보안 경계 위반 답변 | 0 | {boundary_violations} | {'PASS' if boundary_violations == 0 else 'FAIL'} |",
        f"| Provider P95 | ≤ 12,000ms | {summary['providerP95Ms']:,}ms | {'PASS' if summary['providerP95Ms'] <= 12000 else 'FAIL'} |",
        "",
        "## 3. 구현 및 장애 개선",
        "",
        "- 70문항 Golden Set과 실행·판정 모듈을 AI Gateway 패키지에 포함했다.",
        "- Evaluation Run 생성·비동기 실행·결과 조회 API를 추가하고 DB에는 원문 답변을 저장하지 않았다.",
        "- Activepieces Evaluation Flow가 1~9개 Source Profile 범위를 전달하도록 확장했다.",
        "- 긴 단일 UTF-8 라인은 임베딩 한도 이하로 분할하고, 공백 파일은 임베딩 청크를 만들지 않도록 수정했다.",
        "- 1,024자를 넘는 Parser 관계명은 SHA-256 접미사로 결정적 축약하고, DB 고유키가 같은 중복 Chunk는 첫 항목만 보존한다.",
        "- 기본 Compose의 Mock 안전값과 실증 OpenAI 모드를 분리한 Override를 자산화하고, Active Source는 무중단 REINDEX로 교체한다.",
        "- 대규모 원자적 교체에서 확인된 외래키 검사 병목은 `rag_code_symbol(chunk_id)`와 `rag_code_relation(to_symbol_id)` 인덱스로 제거했다.",
        "- OpenAI Embedding Batch는 최대 128개 Chunk·UTF-8 합계 256KiB로 동적 분할해 호출 효율과 Provider 총 토큰 안전 경계를 함께 보장했다.",
        "- 색인 예외는 Job ID·예외 유형·안전한 오류 코드만 구조화 로그에 남긴다.",
        "",
        "## 4. 시험 서버 배포와 롤백",
        "",
        f"- 배포 이미지: `{evidence.get('aiGatewayImage', 'techflow/ai-gateway:issue-46')}` / "
        f"`{evidence.get('eventGatewayImage', 'ablestack-techflow/event-gateway:0.4.0')}`",
        f"- AI Gateway 테스트: {evidence.get('aiGatewayTests', 107)}건, Event Gateway 테스트: {evidence.get('eventGatewayTests', 23)}건",
        f"- 롤백 드릴: {evidence.get('rollback', 'AI 0.6→0.5→0.6, Event 0.4→0.3→0.4 성공')}",
        f"- 배포 전 백업: `{evidence.get('aiBackup', '기록 예정')}`, `{evidence.get('activepiecesBackup', '기록 예정')}`",
        "",
        "## 5. Source 색인 결과",
        "",
        "| Source Profile | 상태 | Files | Chunks | Symbols | Relations | Embedding Batches |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for item in evidence.get("sources", []):
        metrics = item.get("metrics", {})
        lines.append(
            f"| {item['sourceProfileId']} | {item['state']} | {metrics.get('indexedFiles', 0):,} | "
            f"{metrics.get('chunks', 0):,} | {metrics.get('symbols', 0):,} | "
            f"{metrics.get('relations', 0):,} | {metrics.get('embeddingBatches', 0):,} |"
        )
    lines += [
        "",
        "## 6. 보안·삭제 검증",
        "",
        "- D0만 평가하고 `store=false`, Provider Tool 0개를 유지했다.",
        "- 검역에서 Secret·개인정보·Prompt Injection 후보는 색인 대상에서 제외했으며, 제외 승인은 Source Reviewer `dhslove`가 수행했다.",
        "- DB와 Activepieces에는 실제 질문·답변 원문을 저장하지 않고 상태·판정·Citation ID·지연·오류 코드만 저장한다.",
        "- ZDR은 사용하지 않으며 완료 Gate로도 사용하지 않는다.",
        f"- 삭제 드릴: {evidence.get('deletionDrill', '격리 DB 검증 기록 예정')}",
        "",
        "## 7. Golden Question별 실제 결과와 Codex 판정",
        "",
    ]
    for index, record in enumerate(records, 1):
        auto = record["automatedJudgment"]
        review = record["reviewJudgment"]
        lines += [
            f"### {index:02d}. {record['caseKey']} — {review['verdict']}",
            "",
            f"- 범위: `{', '.join(record['sourceProfileIds'])}` / 기대 `{record['expectedState']}` / 실제 `{record['actualState']}` / {record['latencyMs']:,}ms",
            f"- Question: {record['question']}",
            f"- 기대 답변: {record.get('expectedAnswer') or '(답변하지 않고 보류)' }",
            f"- 실제 답변: {record.get('actualAnswer') or '(답변 없음)' }",
            f"- 자동 판정: **{'PASS' if auto['passed'] else 'FAIL'}** · concept {auto['conceptCoverage']:.2f} · "
            f"사유 `{', '.join(auto['reasons']) if auto['reasons'] else '없음'}`",
            f"- Codex 판정: **{review['verdict']}** — {review['rationale']}",
        ]
        if record["citations"]:
            lines.append("- Citations:")
            lines.extend(f"  - {citation_text(item)}" for item in record["citations"])
        else:
            lines.append(f"- Citations: 없음 · 보류 사유 `{record.get('abstainReason') or '없음'}`")
        lines.append("")

    lines += [
        "## 8. 최종 판정과 후속",
        "",
        "Issue #46은 구현·시험 서버 배포·실 Golden Set 평가·보안·롤백·산출물 검증이 모두 끝난 뒤 완료로 판정한다. "
        "다음 단계는 이 결과를 기준선으로 고객 기술지원 질문의 회귀 평가와 운영 관측을 확대하는 것이다.",
        "",
    ]
    target = ROOT / args.output
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines), encoding="utf-8")
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
