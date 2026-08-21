# Issue #22 결과물 빌드

Issue #22 Chat 기반 Community 승인 보고서 PDF와 발표자료 PPTX·PDF, SHA-256 Manifest를 재생성한다.

1. Codex Presentations Skill의 Codex Grid Layout `10`, `17`, `19`, `26`, `runtime.mjs`, `content-tokens.json`을 `tmp/artifacts/issue-22/grid`에 복사한다.
2. Artifact Tool Workspace를 같은 임시 디렉터리에 초기화한다.
3. `build_presentation.mjs`를 임시 디렉터리로 복사해 PPTX와 PNG QA Render를 만든다.
4. `build_report.py`와 `build_presentation_pdf.py`로 PDF 두 개를 만든다.
5. `build_manifest.py`와 `validate_artifacts.py`를 실행한다.
6. 모든 PDF Page와 PPTX Slide를 이미지로 렌더링해 넘침·겹침·잘림을 시각 검수한다.

Runtime Secret, Token, Webhook URL, 비밀번호와 인증 응답은 결과물 입력에 포함하지 않는다.
