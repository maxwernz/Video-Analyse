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
`requirements.txt`, `environment.yml`, and `app_builder.sh` are retained as legacy
reference material and must not be used to create a development environment.

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
