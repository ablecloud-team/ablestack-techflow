# Issue #43 Artifact Builder

최종 산출물:

- `output/pdf/techflow-parser-embedding-report.pdf`
- `output/pdf/techflow-parser-embedding-presentation.pdf`
- `output/presentation/techflow-parser-embedding.pptx`
- `output/issue-43-artifact-manifest.json`

PPTX는 Presentation Skill의 `@oai/artifact-tool` Template-following 방식으로 생성하고, PDF 보고서는 ReportLab으로 생성합니다. 모든 PDF 페이지와 PPTX 슬라이드는 PNG로 렌더링해 시각 검수합니다.

## 재생성 순서

1. `output/presentation/techflow-source-registry.pptx`를 기준 템플릿으로 검사합니다.
2. `template-frame-map.json`과 Presentation Skill의
   `prepare_template_starter_deck.mjs`를 사용해
   `tmp/issue43-presentation/template-starter.pptx`를 생성합니다.
3. 저장소 루트에서 아래 명령으로 PPTX를 생성합니다.

```powershell
$env:NODE_PATH = '<workspace-dependencies>/node/node_modules'
node tools/artifacts/issue-43/build_presentation.mjs .
```

4. `build_report.py`, `build_presentation_pdf.py`,
   `build_manifest.py`, `validate_artifacts.py` 순으로 PDF·Manifest를
   생성하고 검증합니다.
5. PPTX 10장과 PDF 18페이지 전체를 PNG로 렌더링해 육안 검수하고,
   `slides_test.py`와 Template Fidelity 검사 결과가 모두 PASS인지 확인합니다.

`template-audit.txt`와 `deviation-log.txt`는 템플릿 분석 및 예외 선택의
재현 근거입니다. 생성기에는 비밀번호, API Key, Session, Cookie를 입력하지
않습니다.
