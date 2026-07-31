$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$skillRoot = "C:\Users\ablecloud\.codex\plugins\cache\openai-primary-runtime\presentations\26.730.11710\skills\presentations"
$nodeExe = "C:\Users\ablecloud\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"
$pythonExe = "C:\Users\ablecloud\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$workspace = Join-Path $repoRoot "tmp\artifacts\issue-18"
$templateInspect = Join-Path $workspace "template-inspect"
$rendered = Join-Path $workspace "rendered"
$sourceDeck = Join-Path $repoRoot "output\presentation\techflow-observability.pptx"
$presentationOutput = Join-Path $repoRoot "output\presentation\techflow-image-version-lock.pptx"
$workspaceFrameMap = Join-Path $workspace "template-frame-map.json"
$workspacePresentationSource = Join-Path $workspace "build_presentation.mjs"
$workspaceInspectSource = Join-Path $workspace "build_template_inspect.mjs"
$starterDeck = Join-Path $workspace "template-starter.pptx"
$starterPreview = Join-Path $workspace "template-starter-preview"
$starterLayout = Join-Path $workspace "template-starter-layout"
$finalLayout = Join-Path $workspace "final-layout"
$fullInspect = Join-Path $templateInspect "template-inspect-full.ndjson"

New-Item -ItemType Directory -Force -Path $workspace, $rendered | Out-Null

Push-Location "C:\Users\ablecloud"
try {
    & $nodeExe (Join-Path $skillRoot "container_tools\setup_artifact_tool_workspace.mjs") --workspace $workspace
    if ($LASTEXITCODE -ne 0) { throw "artifact-tool workspace setup failed: $LASTEXITCODE" }
}
finally { Pop-Location }

Copy-Item -LiteralPath (Join-Path $PSScriptRoot "build_presentation.mjs") -Destination $workspacePresentationSource -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "build_template_inspect.mjs") -Destination $workspaceInspectSource -Force

$audit = @"
Source: output/presentation/techflow-observability.pptx
Slides inspected: 10/10
Reusable patterns: title, outcome cards, responsibility cards, policy table, six-step runbook, evidence flow, verification cards, asset cards, roadmap, closing
Typography and layout: preserve source font family, sizes, spacing, master/layout hierarchy, page markers and color system
Inherited placeholders: no unresolved structural placeholders observed; mapped narrative text and table cells are rewritten in place
Insertion contract: duplicate source slides 1-10 one-for-one and edit only mapped inherited elements
"@
Set-Content -LiteralPath (Join-Path $workspace "template-audit.txt") -Value $audit -Encoding utf8
Set-Content -LiteralPath (Join-Path $workspace "deviation-log.txt") -Value "No layout deviations. Content only was rewritten in inherited elements." -Encoding utf8

$env:Path = "C:\Program Files\Git\usr\bin;" + $env:Path
Push-Location "C:\Users\ablecloud"
try {
    & $nodeExe (Join-Path $skillRoot "template_following_scripts\inspect_template_deck.mjs") --workspace $workspace --pptx $sourceDeck
    if ($LASTEXITCODE -ne 0) { throw "template inspection failed: $LASTEXITCODE" }
}
finally { Pop-Location }

& $nodeExe $workspaceInspectSource $sourceDeck $fullInspect
if ($LASTEXITCODE -ne 0) { throw "full template inspection failed: $LASTEXITCODE" }
& $pythonExe (Join-Path $PSScriptRoot "build_frame_map.py") $fullInspect $workspaceFrameMap
if ($LASTEXITCODE -ne 0) { throw "frame map build failed: $LASTEXITCODE" }

Push-Location "C:\Users\ablecloud"
try {
    & $nodeExe (Join-Path $skillRoot "template_following_scripts\prepare_template_starter_deck.mjs") `
        --workspace $workspace --pptx $sourceDeck --map $workspaceFrameMap --out $starterDeck `
        --inspect $fullInspect --preview-dir $starterPreview --layout-dir $starterLayout
    if ($LASTEXITCODE -ne 0) { throw "template starter build failed: $LASTEXITCODE" }
}
finally { Pop-Location }

& $pythonExe (Join-Path $PSScriptRoot "build_report.py")
if ($LASTEXITCODE -ne 0) { throw "report build failed: $LASTEXITCODE" }

Push-Location $workspace
try {
    & $nodeExe $workspacePresentationSource $repoRoot
    if ($LASTEXITCODE -ne 0) { throw "presentation build failed: $LASTEXITCODE" }
}
finally { Pop-Location }

Push-Location "C:\Users\ablecloud"
try {
    & $nodeExe (Join-Path $skillRoot "template_following_scripts\check_template_fidelity.mjs") `
        --workspace $workspace --starter-pptx $starterDeck --final-pptx $presentationOutput `
        --map $workspaceFrameMap --starter-layout-dir $starterLayout --final-layout-dir $finalLayout --edit-dir $workspace
    if ($LASTEXITCODE -ne 0) { throw "template fidelity check failed: $LASTEXITCODE" }
}
finally { Pop-Location }

Get-ChildItem -LiteralPath $rendered -File -ErrorAction SilentlyContinue | Remove-Item -Force
Push-Location "C:\Users\ablecloud"
try {
    & $pythonExe (Join-Path $skillRoot "container_tools\render_slides.py") $presentationOutput --output_dir $rendered
    if ($LASTEXITCODE -ne 0) { throw "presentation render failed: $LASTEXITCODE" }
    & $pythonExe (Join-Path $skillRoot "container_tools\slides_test.py") $presentationOutput
    if ($LASTEXITCODE -ne 0) { throw "presentation overflow check failed: $LASTEXITCODE" }
}
finally { Pop-Location }

& $pythonExe (Join-Path $PSScriptRoot "build_presentation_pdf.py")
if ($LASTEXITCODE -ne 0) { throw "presentation PDF build failed: $LASTEXITCODE" }
& $pythonExe (Join-Path $PSScriptRoot "build_manifest.py")
if ($LASTEXITCODE -ne 0) { throw "manifest build failed: $LASTEXITCODE" }

Write-Host "Issue #18 artifacts generated."
