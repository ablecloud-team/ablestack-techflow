# Issue #46 artifact builders

Golden Set 생성부터 실제 Gateway 평가, Markdown/PDF 보고서, PPTX/PDF 발표자료, Manifest 검증까지 재현한다.

1. `build_golden_set.py`와 `tools/ai_gateway/validate_issue_46.py`
2. `remote_exec.py`·`server_api.py`로 비밀정보 없는 서버 배포·상태 수집
3. `send_evaluation_event.py`로 Event Gateway 내부의 런타임 Secret을 사용한 서명 E2E
4. `run_golden_evaluation.py --mode live`
5. `build_markdown_report.py`
6. `build_report.py`
7. `build_presentation.mjs`와 `build_presentation_pdf.py`
8. 모든 PDF·PPTX 렌더링 검사
9. `build_manifest.py`
10. `validate_artifacts.py`

실 평가 원문은 승인된 D0 Golden Question만 포함하며 운영 DB와 Activepieces에는 저장하지 않는다.
