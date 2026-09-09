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
uv run mypy main.py app_runtime.py video_creator.py
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
