<#
.SYNOPSIS
    Build the authoritative unsigned x64 Windows package for Video Analyse.

.DESCRIPTION
    The same command runs locally and in CI. It produces
    dist\Video-Analyse-<version>-x64-setup.exe, a per-user installer carrying the
    packaged application, and fails if the packaged application cannot complete
    its smoke check.

    Requires uv and Inno Setup 6 (ISCC.exe). Install Inno Setup with
    `winget install JRSoftware.InnoSetup` if it is not already present.
#>

[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

$applicationName = "Video Analyse"
$packagedApplication = Join-Path $projectRoot "dist\$applicationName"
$executable = Join-Path $packagedApplication "$applicationName.exe"

if (-not $IsWindows) {
    throw "This build must run natively on Windows."
}
if ($env:PROCESSOR_ARCHITECTURE -ne "AMD64") {
    throw "This build must run natively on x64 Windows, not $env:PROCESSOR_ARCHITECTURE."
}

function Resolve-InnoSetupCompiler {
    $onPath = Get-Command "ISCC.exe" -ErrorAction SilentlyContinue
    if ($onPath) { return $onPath.Source }

    foreach ($programFiles in @($env:ProgramFiles, ${env:ProgramFiles(x86)})) {
        if (-not $programFiles) { continue }
        $candidate = Join-Path $programFiles "Inno Setup 6\ISCC.exe"
        if (Test-Path $candidate) { return $candidate }
    }

    throw "Inno Setup 6 (ISCC.exe) was not found. Install it with 'winget install JRSoftware.InnoSetup'."
}

$innoSetupCompiler = Resolve-InnoSetupCompiler

Write-Host "==> Installing locked dependencies"
uv sync --locked --all-groups

$version = (uv run python -c "import build_config.shared as s; print(s.application_version())").Trim()

Write-Host "==> Building $applicationName $version for x64"
Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue
uv run pyinstaller build_config/windows.spec --noconfirm --distpath dist --workpath build

if (-not (Test-Path $executable)) {
    throw "PyInstaller did not produce $executable."
}

Write-Host "==> Running the packaged smoke check"
# The packaged application is windowed, so it owns no console: PowerShell would
# neither wait for it nor see its output. Start-Process waits for the exit code
# and VIDEO_ANALYSE_SMOKE_REPORT carries the report back through a file.
$smokeDirectory = Join-Path ([System.IO.Path]::GetTempPath()) ("video-analyse-smoke-" + [System.Guid]::NewGuid())
New-Item -ItemType Directory -Path $smokeDirectory | Out-Null
$smokeReport = Join-Path $smokeDirectory "smoke-report.json"
try {
    $env:QT_QPA_PLATFORM = "offscreen"
    $env:VIDEO_ANALYSE_LOG_DIR = Join-Path $smokeDirectory "logs"
    $env:VIDEO_ANALYSE_SMOKE_REPORT = $smokeReport

    $smoke = Start-Process -FilePath $executable -ArgumentList "--smoke-test" -Wait -PassThru -NoNewWindow
    if ($smoke.ExitCode -ne 0) {
        throw "The packaged application failed its smoke check with exit code $($smoke.ExitCode)."
    }
    if (-not (Test-Path $smokeReport)) {
        throw "The packaged application reported no smoke result."
    }
    $report = Get-Content -Raw $smokeReport | ConvertFrom-Json
    if ($report.status -ne "ok") {
        throw "The packaged application reported smoke status '$($report.status)'."
    }
    Write-Host "    bundled font: $($report.font)"
}
finally {
    Remove-Item -Recurse -Force $smokeDirectory -ErrorAction SilentlyContinue
    Remove-Item env:QT_QPA_PLATFORM, env:VIDEO_ANALYSE_LOG_DIR, env:VIDEO_ANALYSE_SMOKE_REPORT -ErrorAction SilentlyContinue
}

$installer = Join-Path $projectRoot "dist\Video-Analyse-$version-x64-setup.exe"
Write-Host "==> Creating $installer"
& $innoSetupCompiler `
    "/DApplicationVersion=$version" `
    "/DSourceDirectory=$packagedApplication" `
    "/DOutputDirectory=$(Join-Path $projectRoot 'dist')" `
    "/DIconFile=$(Join-Path $projectRoot 'icons\app_icon.ico')" `
    "build_config/windows_installer.iss"

if (-not (Test-Path $installer)) {
    throw "Inno Setup did not produce $installer."
}

Write-Host "==> Built $installer"
