<#
.SYNOPSIS
    Launches Roadmap Studio for this repository on localhost.
#>
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$SkillScript = Join-Path $env:USERPROFILE ".gemini\config\skills\roadmap-studio\scripts\roadmap_studio_ctl.py"

if (-not (Test-Path $SkillScript)) {
    Write-Error "roadmap_studio_ctl.py not found at $SkillScript. Run sync.py --deploy from antigravity-toolkit first."
    exit 1
}

$PythonExe = "C:\msys64\mingw64\bin\python.exe"
if (-not (Test-Path $PythonExe)) {
    $Cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($Cmd -and (Get-Item $Cmd.Source).Length -gt 0) {
        $PythonExe = $Cmd.Source
    } else {
        Write-Error "Python 3 executable not found."
        exit 1
    }
}

& $PythonExe $SkillScript serve $RepoRoot --open
