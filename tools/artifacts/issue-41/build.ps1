$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$skillRoot = "C:\Users\ablecloud\.codex\plugins\cache\openai-primary-runtime\presentations\26.802.11031\skills\presentations"
$nodeExe = "C:\Users\ablecloud\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"
$pythonExe = "C:\Users\ablecloud\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$workspace = Join-Path $repoRoot "tmp\issue-41-artifacts"
$sourceDeck = Join-Path $repoRoot "output\presentation\techflow-rag-poc-design.pptx"
$sourceInspect = Join-Path $workspace "source-full-inspect.ndjson"
$frameMap = Join-Path $workspace "template-frame-map.json"
$starterDeck = Join-Path $workspace "template-starter.pptx"
$starterPreview = Join-Path $workspace "template-starter-preview"
$starterLayout = Join-Path $workspace "template-starter-layout"
$finalLayout = Join-Path $workspace "final-layout"
$rendered = Join-Path $workspace "rendered"
$presentationOutput = Join-Path $repoRoot "output\presentation\techflow-ai-gateway-foundation.pptx"
$workspacePresentationSource = Join-Path $workspace "build-presentation.mjs"
$workspaceInspectSource = Join-Path $workspace "build-full-inspect.mjs"

New-Item -ItemType Directory -Force -Path $workspace, $rendered | Out-Null
Push-Location "C:\Users\ablecloud"
try {
    & $nodeExe (Join-Path $skillRoot "container_tools\setup_artifact_tool_workspace.mjs") --workspace $workspace
    if ($LASTEXITCODE -ne 0) { throw "artifact-tool workspace setup failed: $LASTEXITCODE" }
}
finally { Pop-Location }

Copy-Item -LiteralPath (Join-Path $PSScriptRoot "build_presentation.mjs") -Destination $workspacePresentationSource -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "build_full_inspect.mjs") -Destination $workspaceInspectSource -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "template-audit.txt") -Destination (Join-Path $workspace "template-audit.txt") -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "deviation-log.txt") -Destination (Join-Path $workspace "deviation-log.txt") -Force
& $nodeExe $workspaceInspectSource $sourceDeck $sourceInspect
if ($LASTEXITCODE -ne 0) { throw "full source inspection failed: $LASTEXITCODE" }
& $pythonExe (Join-Path $PSScriptRoot "build_frame_map.py") $sourceInspect $frameMap
if ($LASTEXITCODE -ne 0) { throw "frame map build failed: $LASTEXITCODE" }

$env:Path = "C:\Program Files\Git\usr\bin;" + $env:Path
Push-Location "C:\Users\ablecloud"
try {
    & $nodeExe (Join-Path $skillRoot "template_following_scripts\prepare_template_starter_deck.mjs") `
        --workspace $workspace --pptx $sourceDeck --map $frameMap --inspect $sourceInspect `
        --out $starterDeck --preview-dir $starterPreview --layout-dir $starterLayout
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
        --map $frameMap --starter-layout-dir $starterLayout --final-layout-dir $finalLayout --edit-dir $workspace
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
    & $pythonExe (Join-Path $skillRoot "container_tools\create_montage.py") --input_dir $rendered --output_file (Join-Path $workspace "final-contact-sheet.png")
    if ($LASTEXITCODE -ne 0) { throw "presentation montage failed: $LASTEXITCODE" }
}
finally { Pop-Location }

& $pythonExe (Join-Path $PSScriptRoot "build_presentation_pdf.py")
if ($LASTEXITCODE -ne 0) { throw "presentation PDF build failed: $LASTEXITCODE" }
& $pythonExe (Join-Path $PSScriptRoot "build_manifest.py")
if ($LASTEXITCODE -ne 0) { throw "manifest build failed: $LASTEXITCODE" }
& $pythonExe (Join-Path $PSScriptRoot "validate_artifacts.py")
if ($LASTEXITCODE -ne 0) { throw "artifact validation failed: $LASTEXITCODE" }

Write-Host "Issue #41 artifacts generated and validated."
