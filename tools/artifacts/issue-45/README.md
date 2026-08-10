# Issue #45 보고 자산 빌드

Issue #45의 Markdown 보고서와 동일한 근거로 PDF 보고서, PPTX, 발표자료 PDF와 무결성 Manifest를 관리한다.

```powershell
python tools/artifacts/issue-45/build_report.py
node tmp/issue-44-artifacts/build-deck-45.mjs
python tools/artifacts/issue-45/build_presentation_pdf.py
python tools/artifacts/issue-45/build_manifest.py
python tools/artifacts/issue-45/validate_artifacts.py
```

PPTX는 `presentations` 스킬의 Codex Grid Layout Library와 Artifact Tool로 생성한다. 최종 9개 Slide PNG는 `tmp/issue-45-artifacts/rendered/`에 두며 발표자료 PDF는 이 시각 검수본을 사용한다. 모든 Slide Speaker Notes에는 `[Sources]` 블록이 있어야 한다.
