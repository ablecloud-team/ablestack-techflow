# Issue #72 결과물 빌드

Issue #72 Community 대용량 첨부 개선 보고서와 발표자료를 재생성한다.

## 입력

- `docs/evidence/issue-72/large-upload-production-validation.json`
- `docs/reports/issue-72-community-large-upload-validation.md`
- `docs/runbooks/community-large-uploads.md`

## 출력

- `output/pdf/techflow-issue-72-large-upload-report.pdf`
- `output/presentation/techflow-issue-72-large-upload.pptx`
- `output/pdf/techflow-issue-72-large-upload-presentation.pdf`
- `output/issue-72-large-upload-artifact-manifest.json`

실행 환경은 Codex bundled Python/Node와 Presentation artifact-tool을 사용한다. 빌드 후 `validate_artifacts.py`로 페이지 수, 파일 크기, 구조화 증적, 비밀정보 미포함을 검증한다.

