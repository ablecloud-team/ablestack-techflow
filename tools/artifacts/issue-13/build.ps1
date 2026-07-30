$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$skillRoot = "C:\Users\ablecloud\.codex\plugins\cache\openai-primary-runtime\presentations\26.727.11326\skills\presentations"
$nodeExe = "C:\Users\ablecloud\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"
$pythonExe = "C:\Users\ablecloud\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$workspace = Join-Path $repoRoot "tmp\artifacts\issue-13"
$templateInspect = Join-Path $workspace "template-inspect"
$rendered = Join-Path $workspace "rendered"
$sourceDeck = Join-Path $repoRoot "output\presentation\activepieces-license-review.pptx"
$presentationOutput = Join-Path $repoRoot "output\presentation\activepieces-compose-deployment.pptx"
$frameMap = Join-Path $PSScriptRoot "template-frame-map.json"
$workspaceFrameMap = Join-Path $workspace "template-frame-map.json"
$workspacePresentationSource = Join-Path $workspace "build_presentation.mjs"
$workspaceInspectSource = Join-Path $workspace "build_template_inspect.mjs"
$starterDeck = Join-Path $workspace "template-starter.pptx"
$starterPreview = Join-Path $workspace "template-starter-preview"
$starterLayout = Join-Path $workspace "template-starter-layout"
$finalLayout = Join-Path $workspace "final-layout"

New-Item -ItemType Directory -Force -Path $workspace, $rendered | Out-Null

Push-Location "C:\Users\ablecloud"
try {
    & $nodeExe (Join-Path $skillRoot "container_tools\setup_artifact_tool_workspace.mjs") --workspace $workspace
    if ($LASTEXITCODE -ne 0) { throw "artifact-tool workspace setup failed: $LASTEXITCODE" }
}
finally {
    Pop-Location
}

Copy-Item -LiteralPath $frameMap -Destination $workspaceFrameMap -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "build_presentation.mjs") -Destination $workspacePresentationSource -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "build_template_inspect.mjs") -Destination $workspaceInspectSource -Force

$env:Path = "C:\Program Files\Git\usr\bin;" + $env:Path
Push-Location "C:\Users\ablecloud"
try {
    & $nodeExe (Join-Path $skillRoot "template_following_scripts\inspect_template_deck.mjs") --workspace $workspace --pptx $sourceDeck
    if ($LASTEXITCODE -ne 0) { throw "template inspection failed: $LASTEXITCODE" }
}
finally {
    Pop-Location
}

& $nodeExe $workspaceInspectSource $sourceDeck (Join-Path $templateInspect "template-inspect.ndjson")
if ($LASTEXITCODE -ne 0) { throw "full template inspection failed: $LASTEXITCODE" }

Push-Location "C:\Users\ablecloud"
try {
    & $nodeExe (Join-Path $skillRoot "template_following_scripts\prepare_template_starter_deck.mjs") `
        --workspace $workspace `
        --pptx $sourceDeck `
        --map $workspaceFrameMap `
        --out $starterDeck `
        --preview-dir $starterPreview `
        --layout-dir $starterLayout
    if ($LASTEXITCODE -ne 0) { throw "template starter build failed: $LASTEXITCODE" }
}
finally {
    Pop-Location
}

& $pythonExe (Join-Path $PSScriptRoot "build_report.py")
if ($LASTEXITCODE -ne 0) { throw "report build failed: $LASTEXITCODE" }

Push-Location $workspace
try {
    & $nodeExe $workspacePresentationSource $repoRoot
    if ($LASTEXITCODE -ne 0) { throw "presentation build failed: $LASTEXITCODE" }
}
finally {
    Pop-Location
}

Push-Location "C:\Users\ablecloud"
try {
    & $nodeExe (Join-Path $skillRoot "template_following_scripts\check_template_fidelity.mjs") `
        --workspace $workspace `
        --starter-pptx $starterDeck `
        --final-pptx $presentationOutput `
        --map $workspaceFrameMap `
        --starter-layout-dir $starterLayout `
        --final-layout-dir $finalLayout `
        --edit-dir $workspace
    if ($LASTEXITCODE -ne 0) { throw "template fidelity check failed: $LASTEXITCODE" }
}
finally {
    Pop-Location
}

Get-ChildItem -LiteralPath $rendered -File -ErrorAction SilentlyContinue | Remove-Item -Force
Push-Location "C:\Users\ablecloud"
try {
    & $pythonExe (Join-Path $skillRoot "container_tools\render_slides.py") $presentationOutput --output_dir $rendered
    if ($LASTEXITCODE -ne 0) { throw "presentation render failed: $LASTEXITCODE" }
    & $pythonExe (Join-Path $skillRoot "container_tools\slides_test.py") $presentationOutput
    if ($LASTEXITCODE -ne 0) { throw "presentation overflow check failed: $LASTEXITCODE" }
}
finally {
    Pop-Location
}

& $pythonExe (Join-Path $PSScriptRoot "build_presentation_pdf.py")
if ($LASTEXITCODE -ne 0) { throw "presentation PDF build failed: $LASTEXITCODE" }
& $pythonExe (Join-Path $PSScriptRoot "build_manifest.py")
if ($LASTEXITCODE -ne 0) { throw "manifest build failed: $LASTEXITCODE" }

Write-Host "Issue #13 artifacts generated."
