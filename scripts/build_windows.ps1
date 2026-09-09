<#
.SYNOPSIS
    Build the authoritative unsigned x64 Windows package for Video Analyse.

.DESCRIPTION
    The same command runs locally and in CI. It produces
    dist\Video-Analyse-<version>-x64-setup.exe, a per-user installer carrying the
    packaged application, and fails if the packaged application cannot complete
    its smoke check.

    Requires uv and Inno Setup 6.3 or newer (ISCC.exe). Install Inno Setup with
    `winget install JRSoftware.InnoSetup` or `choco install innosetup`.
#>

[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

# $IsWindows exists only in PowerShell 6 and newer, so ask the platform itself.
if ($env:OS -ne "Windows_NT") {
    throw "This build must run natively on Windows."
}
if ($env:PROCESSOR_ARCHITECTURE -ne "AMD64") {
    throw "This build must run natively on x64 Windows, not $env:PROCESSOR_ARCHITECTURE."
}

$minimumInnoSetupVersion = [version]"6.3"

function Resolve-InnoSetupCompiler {
    <#
        The installer uses the x64compatible architecture identifier, which
        Inno Setup only understands from 6.3 onwards, so an older compiler must
        be reported here rather than as an obscure compilation error.
    #>

    $candidates = @()
    $onPath = Get-Command "ISCC.exe" -ErrorAction SilentlyContinue
    if ($onPath) { $candidates += $onPath.Source }
    foreach ($programFiles in @($env:ProgramFiles, ${env:ProgramFiles(x86)})) {
        if ($programFiles) { $candidates += (Join-Path $programFiles "Inno Setup 6\ISCC.exe") }
    }

    foreach ($candidate in $candidates) {
        if (-not (Test-Path $candidate)) { continue }

        $reported = (Get-Item $candidate).VersionInfo.ProductVersion
        $found = [version]($reported -replace '^(\d+(\.\d+)*).*$', '$1')
        if ($found -lt $minimumInnoSetupVersion) {
            Write-Warning "Ignoring Inno Setup $found at $candidate; $minimumInnoSetupVersion or newer is required."
            continue
        }
        return $candidate
    }

    throw "Inno Setup $minimumInnoSetupVersion or newer (ISCC.exe) was not found. Install it with 'winget install JRSoftware.InnoSetup'."
}

$innoSetupCompiler = Resolve-InnoSetupCompiler

Write-Host "==> Installing locked dependencies"
uv sync --locked --all-groups

# build_config/shared.py is the single owner of application metadata; reading it
# here keeps the installer from restating the name, publisher, or version.
$metadata = uv run python -c "import json; import build_config.shared as shared; print(json.dumps({'name': shared.APPLICATION_NAME, 'publisher': shared.PUBLISHER, 'version': shared.application_version(), 'installer': shared.artifact_name('x64-setup')}))" | ConvertFrom-Json

$applicationName = $metadata.name
$packagedApplication = Join-Path $projectRoot "dist\$applicationName"
$executable = Join-Path $packagedApplication "$applicationName.exe"
$installer = Join-Path $projectRoot "dist\$($metadata.installer).exe"

Write-Host "==> Building $applicationName $($metadata.version) for x64"
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
$smokeEnvironment = @{
    QT_QPA_PLATFORM             = "offscreen"
    VIDEO_ANALYSE_LOG_DIR       = (Join-Path $smokeDirectory "logs")
    VIDEO_ANALYSE_SMOKE_REPORT  = $smokeReport
}
$previousEnvironment = @{}
foreach ($name in $smokeEnvironment.Keys) {
    $previousEnvironment[$name] = [System.Environment]::GetEnvironmentVariable($name)
}
try {
    foreach ($name in $smokeEnvironment.Keys) {
        [System.Environment]::SetEnvironmentVariable($name, $smokeEnvironment[$name])
    }

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
    foreach ($name in $smokeEnvironment.Keys) {
        [System.Environment]::SetEnvironmentVariable($name, $previousEnvironment[$name])
    }
    Remove-Item -Recurse -Force $smokeDirectory -ErrorAction SilentlyContinue
}

Write-Host "==> Creating $installer"
& $innoSetupCompiler `
    "/DApplicationName=$applicationName" `
    "/DApplicationVersion=$($metadata.version)" `
    "/DPublisher=$($metadata.publisher)" `
    "/DExecutableName=$applicationName.exe" `
    "/DOutputBaseFilename=$($metadata.installer)" `
    "/DSourceDirectory=$packagedApplication" `
    "/DOutputDirectory=$(Join-Path $projectRoot 'dist')" `
    "/DIconFile=$(Join-Path $projectRoot 'icons\app_icon.ico')" `
    "build_config/windows_installer.iss"

if (-not (Test-Path $installer)) {
    throw "Inno Setup did not produce $installer."
}

Write-Host "==> Built $installer"
