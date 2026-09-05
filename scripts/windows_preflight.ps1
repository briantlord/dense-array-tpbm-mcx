param(
    [Parameter(Mandatory = $true)]
    [string]$McxclBinary,

    [ValidateSet("rtx3080", "rtx3080ti")]
    [string]$Target = "rtx3080"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $ProjectRoot

if ($env:OS -ne "Windows_NT") {
    throw "This handoff preflight must run in Windows PowerShell."
}
if (-not (Test-Path -LiteralPath $McxclBinary -PathType Leaf)) {
    throw "MCX-CL executable not found: $McxclBinary"
}

$GitStatus = git status --porcelain --untracked-files=all
if ($LASTEXITCODE -ne 0) {
    throw "Unable to inspect Git status."
}
if ($GitStatus) {
    throw "The repository is not clean. Ask the new chat to inspect the changes before continuing."
}

$Python = Join-Path $ProjectRoot ".venv-win\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    py -3.13 -m venv .venv-win
    if ($LASTEXITCODE -ne 0) {
        throw "Python 3.13 virtual-environment creation failed."
    }
}

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "Install uv, then rerun this script. Dependency installation requires the committed uv.lock."
}
$env:UV_PROJECT_ENVIRONMENT = Join-Path $ProjectRoot ".venv-win"
uv sync --frozen --group dev
if ($LASTEXITCODE -ne 0) {
    throw "Locked environment synchronization failed."
}

$ResolvedBinary = (Resolve-Path -LiteralPath $McxclBinary).Path
$env:MCXCL_BINARY = $ResolvedBinary
& $ResolvedBinary --version
if ($LASTEXITCODE -ne 0) {
    throw "MCX-CL version probe failed."
}
& $ResolvedBinary --listgpu
if ($LASTEXITCODE -ne 0) {
    throw "MCX-CL GPU probe failed."
}

& $Python -m pytest -q
if ($LASTEXITCODE -ne 0) {
    throw "Repository tests failed. Do not prepare or execute the basis."
}
& $Python -m mcx_project.cli build-surrogate-1070 --project-root . --check
if ($LASTEXITCODE -ne 0) {
    throw "Surrogate freshness check failed."
}
& $Python -m mcx_project.cli freeze-surrogate-basis-plan --project-root . --check
if ($LASTEXITCODE -ne 0) {
    throw "Frozen source-plan check failed."
}
if ($Target -eq "rtx3080ti") {
    & $Python scripts/prepare_windows_rtx3080ti.py --binary $ResolvedBinary --project-root .
} else {
    & $Python scripts/prepare_windows_rtx3080.py --binary $ResolvedBinary --project-root .
}
if ($LASTEXITCODE -ne 0) {
    throw "Windows environment binding failed."
}

Write-Host ""
Write-Host "PREPARED, NOT EXECUTED."
Write-Host "The Windows environment record and distinct basis plan now exist."
Write-Host "Do not run the 277-source batch until the new chat prepares its manifests"
Write-Host "and the SUR1070_011 backend-equivalence gate passes."
