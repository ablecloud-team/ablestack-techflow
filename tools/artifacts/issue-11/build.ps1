$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$skillRoot = "C:\Users\ablecloud\.codex\plugins\cache\openai-primary-runtime\presentations\26.727.11326\skills\presentations"
$nodeExe = "C:\Users\ablecloud\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"
$pythonExe = "C:\Users\ablecloud\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$workspace = Join-Path $repoRoot "tmp\artifacts\issue-11"
$rendered = Join-Path $workspace "rendered"
$presentationSource = Join-Path $PSScriptRoot "build_presentation.mjs"
$presentationWorkspaceSource = Join-Path $workspace "build_presentation.mjs"
$presentationOutput = Join-Path $repoRoot "output\presentation\activepieces-license-review.pptx"

New-Item -ItemType Directory -Force -Path $workspace, $rendered | Out-Null

Push-Location "C:\Users\ablecloud"
try {
    & $nodeExe (Join-Path $skillRoot "container_tools\setup_artifact_tool_workspace.mjs") --workspace $workspace
    if ($LASTEXITCODE -ne 0) { throw "artifact-tool workspace setup failed: $LASTEXITCODE" }
}
finally {
    Pop-Location
}
Copy-Item -LiteralPath $presentationSource -Destination $presentationWorkspaceSource -Force

& $pythonExe (Join-Path $PSScriptRoot "build_report.py")
if ($LASTEXITCODE -ne 0) { throw "report build failed: $LASTEXITCODE" }
& $nodeExe $presentationWorkspaceSource $repoRoot
if ($LASTEXITCODE -ne 0) { throw "presentation build failed: $LASTEXITCODE" }

Get-ChildItem -LiteralPath $rendered -File -ErrorAction SilentlyContinue | Remove-Item -Force
Push-Location "C:\Users\ablecloud"
try {
    & $pythonExe (Join-Path $skillRoot "container_tools\render_slides.py") $presentationOutput --output_dir $rendered
    if ($LASTEXITCODE -ne 0) { throw "presentation render failed: $LASTEXITCODE" }
}
finally {
    Pop-Location
}
& $pythonExe (Join-Path $PSScriptRoot "build_presentation_pdf.py")
if ($LASTEXITCODE -ne 0) { throw "presentation PDF build failed: $LASTEXITCODE" }
& $pythonExe (Join-Path $PSScriptRoot "build_manifest.py")
if ($LASTEXITCODE -ne 0) { throw "manifest build failed: $LASTEXITCODE" }

Write-Host "Issue #11 artifacts generated."
