# Issue #21 결과물 빌드

Issue #21 Community Assist 검증 보고서 PDF와 단계 확인용 PPTX·PDF, SHA-256 Manifest를 재생성한다.

1. Codex Presentations Skill의 Artifact Tool Workspace를 `tmp/artifacts/issue-21`에 초기화한다.
2. Codex Grid의 선택 Layout `01`, `05`, `17`, `19`, `26`과 `runtime.mjs`, `content-tokens.json`을 `tmp/artifacts/issue-21/grid`에 복사한다.
3. `build_presentation.mjs`를 같은 임시 디렉터리로 복사해 Artifact Tool로 PPTX와 PNG QA Render를 만든다.
4. `build_report.py`와 `build_presentation_pdf.py`로 PDF 두 개를 만든다.
5. `build_manifest.py`와 `validate_artifacts.py`를 실행한다.
6. 모든 PDF Page를 PNG로 렌더링해 잘림·겹침·한글 폰트를 시각 검사한다.

Runtime Secret이나 인증 응답은 입력으로 사용하지 않는다.
