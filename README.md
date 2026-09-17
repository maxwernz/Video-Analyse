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

The command initializes Qt, verifies the bundled fonts and overlay font, loads the
bundled Qt Quick scene and waits for the graphics backend to draw it, creates the
diagnostic log, and exits non-zero on any failure. In isolated build environments,
`VIDEO_ANALYSE_LOG_DIR` may point logging at a writable directory.

Qt Quick renders through a graphics backend — Direct3D 11 on Windows, Metal on
macOS. A backend that fails to initialise is detected and the scene is redrawn in
software, so a stale graphics driver makes the application slow rather than
absent. Setting `VIDEO_ANALYSE_SOFTWARE_RENDERING=1` demands software rendering
up front, for a driver that takes the process down instead of reporting a
failure the application could catch.

The application always starts in its QML workspace.

Run all source checks with:

```console
uv run mypy main.py app_runtime.py qml_runtime.py qml_icons.py video_creator.py build_config/shared.py build_config/windows_version_resource.py analysis
uv run python -m pytest
```

Diagnostic logs stay on the device in Qt's operating-system application-data
location. Video Analyse contains no telemetry or automatic log upload.

## Opening legacy Analysis files

The app can import Analysis files written by the original application and asks
you to save the restored Analysis under a new current-format file. Those legacy
files use Python pickle, which can execute code while it is being read. Open a
pickle-based legacy Analysis only when you created it or received it from a
trusted internal source. An unknown pickle cannot be safely inspected or
approved before deserialization, even when it is malformed or appears to be an
Analysis file.

Source videos stay external to every Analysis file. If a restored Analysis
cannot find its Source video, use its relink action to select the moved media;
the Analysis continues with the same Clips and notes rather than embedding or
copying the video.

The interface is set in the bundled Inter and JetBrains Mono; generated video
overlays use the bundled Noto Sans. Their SIL Open Font Licenses are included at
`assets/fonts/OFL-Inter.txt`, `assets/fonts/OFL-JetBrainsMono.txt` and
`assets/fonts/OFL.txt`.

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

On x64 Windows 11 with [Inno Setup](https://jrsoftware.org/isdl.php) 6.3 or newer
installed (`winget install JRSoftware.InnoSetup`, or `choco install innosetup` as
CI does), one command produces the authoritative package that CI publishes:

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

Those tests install, launch, upgrade, and uninstall the real artifact, and they
skip when it has not been built. CI sets `VIDEO_ANALYSE_REQUIRE_PACKAGE=1`, which
turns those skips into failures so a pipeline cannot pass without verifying.

Both packages carry the Qt Quick module tree, and both filter out the Qt modules
PyInstaller's PySide6 hook collects alongside it and this application never
loads — QtWebEngine's roughly 214MB of Chromium above all. `excludes` cannot
reach those, because nothing in Python imports them, so
`build_config/shared.py` filters the collected tables directly and the packaged
size is guarded by a test in both platform suites.

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
