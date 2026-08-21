# Epic #70 산출물 생성

1. `build_report.py`
2. `build_presentation.mjs`
3. `build_presentation_pdf.py`
4. `build_manifest.py`
5. `validate_artifacts.py`

PPTX는 `@oai/artifact-tool`로 생성하며 모든 슬라이드 PNG와 Layout JSON을 `tmp/epic70-presentation/renders`에 남겨 시각·구조 검증한다.
