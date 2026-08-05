$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$skillRoot = "C:\Users\ablecloud\.codex\plugins\cache\openai-primary-runtime\presentations\26.802.11031\skills\presentations"
$nodeExe = "C:\Users\ablecloud\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"
$pythonExe = "C:\Users\ablecloud\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$workspace = Join-Path $repoRoot "tmp\issue-42-artifacts"
$rendered = Join-Path $workspace "rendered"
$workspaceSource = Join-Path $workspace "build-presentation.mjs"
$presentation = Join-Path $repoRoot "output\presentation\techflow-source-registry.pptx"

New-Item -ItemType Directory -Force -Path $workspace, $rendered | Out-Null
Push-Location "C:\Users\ablecloud"
try {
    & $nodeExe (Join-Path $skillRoot "container_tools\setup_artifact_tool_workspace.mjs") --workspace $workspace
    if ($LASTEXITCODE -ne 0) { throw "artifact-tool workspace setup failed: $LASTEXITCODE" }
}
finally { Pop-Location }

Copy-Item -LiteralPath (Join-Path $PSScriptRoot "build_presentation.mjs") -Destination $workspaceSource -Force
& $pythonExe (Join-Path $PSScriptRoot "build_report.py")
if ($LASTEXITCODE -ne 0) { throw "report build failed: $LASTEXITCODE" }

Push-Location $workspace
try {
    & $nodeExe $workspaceSource $repoRoot
    if ($LASTEXITCODE -ne 0) { throw "presentation build failed: $LASTEXITCODE" }
}
finally { Pop-Location }

Get-ChildItem -LiteralPath $rendered -File -ErrorAction SilentlyContinue | Remove-Item -Force
Push-Location "C:\Users\ablecloud"
try {
    & $pythonExe (Join-Path $skillRoot "container_tools\render_slides.py") $presentation --output_dir $rendered
    if ($LASTEXITCODE -ne 0) { throw "presentation render failed: $LASTEXITCODE" }
    & $pythonExe (Join-Path $skillRoot "container_tools\slides_test.py") $presentation
    if ($LASTEXITCODE -ne 0) { throw "presentation overflow check failed: $LASTEXITCODE" }
    & $pythonExe (Join-Path $skillRoot "container_tools\create_montage.py") --input_dir $rendered --output_file (Join-Path $workspace "contact-sheet.png")
    if ($LASTEXITCODE -ne 0) { throw "presentation montage failed: $LASTEXITCODE" }
}
finally { Pop-Location }

& $pythonExe (Join-Path $PSScriptRoot "build_presentation_pdf.py")
if ($LASTEXITCODE -ne 0) { throw "presentation PDF build failed: $LASTEXITCODE" }
& $pythonExe (Join-Path $PSScriptRoot "build_manifest.py")
if ($LASTEXITCODE -ne 0) { throw "manifest build failed: $LASTEXITCODE" }
& $pythonExe (Join-Path $PSScriptRoot "validate_artifacts.py")
if ($LASTEXITCODE -ne 0) { throw "artifact validation failed: $LASTEXITCODE" }

Write-Host "Issue #42 artifacts generated and validated."
