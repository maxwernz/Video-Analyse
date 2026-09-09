# Video Analyse

Video Analyse is a desktop application for reviewing Source videos and exporting
annotated Clips. Development is supported on ARM64 macOS 14 or newer and x64
Windows 11.

## Development setup

Install [uv](https://docs.astral.sh/uv/), then create the exact locked environment:

```console
uv sync --locked --all-groups
```

`pyproject.toml` and `uv.lock` are the only authoritative dependency definition.
`requirements.txt` and `environment.yml` are retained as legacy reference material
and must not be used to create a development environment.

Run the non-interactive application check without showing the normal window:

```console
uv run python main.py --smoke-test
```

The command initializes Qt, constructs the main window, verifies Qt resources and
the bundled overlay font, creates the diagnostic log, and exits non-zero on any
failure. In isolated build environments, `VIDEO_ANALYSE_LOG_DIR` may point logging
at a writable directory.

Run all source checks with:

```console
uv run mypy main.py app_runtime.py video_creator.py build_config/shared.py build_config/windows_version_resource.py analysis
uv run python -m pytest
```

Diagnostic logs stay on the device in Qt's operating-system application-data
location. Video Analyse contains no telemetry or automatic log upload.

Generated video overlays use the bundled Noto Sans font. Its SIL Open Font License
is included at `assets/fonts/OFL.txt`.

## Building the macOS package

On ARM64 macOS 14 or newer, one command produces the authoritative package that
CI publishes:

```console
./scripts/build_macos.sh
```

It installs the locked dependencies, builds `Video Analyse.app` natively for
arm64, verifies the packaged application by running its smoke mode, and writes
`dist/Video-Analyse-<version>-arm64.dmg`. The version comes from
`pyproject.toml`. Continuous integration runs the same script on a macOS ARM64
runner and then verifies the artifact:

```console
uv run python -m pytest tests/test_macos_package.py
```

Packaging configuration is split between `build_config/shared.py`, which owns the
application entry point, dependencies, bundled resources, and metadata shared by
every platform, and `build_config/macos.spec`, which owns macOS details such as
the arm64 target, the bundle identifier, and the macOS 14 minimum system version.

## Installing on macOS

Video Analyse is distributed without an Apple Developer ID identity and without
notarization, so macOS treats it as an unidentified developer. Only open a build
you obtained from this project's own releases.

1. Open the downloaded `Video-Analyse-<version>-arm64.dmg`.
2. Drag **Video Analyse** into the **Applications** folder shown beside it.
3. Open the Applications folder, Control-click **Video Analyse**, and choose
   **Open**.
4. Confirm **Open** in the warning dialog. On macOS 15 or newer, if the dialog
   offers no way to continue, open **System Settings → Privacy & Security**,
   scroll to the message naming Video Analyse, and choose **Open Anyway**.

macOS remembers this decision, so later launches need only a double-click.

## Building the Windows package

On x64 Windows 11 with [Inno Setup 6](https://jrsoftware.org/isdl.php) installed
(`winget install JRSoftware.InnoSetup`), one command produces the authoritative
package that CI publishes:

```console
pwsh ./scripts/build_windows.ps1
```

It installs the locked dependencies, builds `Video Analyse.exe` natively for x64,
verifies the packaged application by running its smoke mode, and writes the
per-user installer `dist\Video-Analyse-<version>-x64-setup.exe`. The version comes
from `pyproject.toml` and reaches both the executable's Windows version resource
and the installer. Continuous integration runs the same script on a Windows x64
runner and then verifies the artifact by installing, launching, upgrading, and
uninstalling it:

```console
uv run python -m pytest tests/test_windows_package.py
```

Windows packaging reuses `build_config/shared.py` unchanged, so entry point,
dependencies, bundled resources, and metadata cannot drift from the macOS
package. `build_config/windows.spec` owns the Windows executable details, and
`build_config/windows_installer.iss` owns the installer.

Because a packaged Windows application has no console, the smoke mode also writes
its report to the file named by `VIDEO_ANALYSE_SMOKE_REPORT` when that variable is
set.

## Installing on Windows

Video Analyse is distributed unsigned, so Windows shows a Microsoft Defender
SmartScreen warning the first time the installer runs. Only run an installer you
obtained from this project's own releases.

1. Run the downloaded `Video-Analyse-<version>-x64-setup.exe`.
2. When SmartScreen reports an unrecognized app, choose **More info** and then
   **Run anyway**.
3. Follow the installer. It installs for your user account only, so Windows never
   asks for administrator rights, and it adds Video Analyse to the Start Menu. A
   desktop shortcut is offered but not preselected.
4. Launch Video Analyse from the Start Menu.

To update, run a newer installer: it upgrades the existing installation in place
and keeps one entry in the installed-apps list. To remove Video Analyse, use
**Settings → Apps → Installed apps → Video Analyse → Uninstall**.
