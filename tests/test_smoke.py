import json
import os
from pathlib import Path
import subprocess
import sys


def run_smoke_check(tmp_path: Path, **overrides: str) -> dict[str, object]:
    environment = os.environ.copy()
    environment["QT_QPA_PLATFORM"] = "offscreen"
    environment["VIDEO_ANALYSE_LOG_DIR"] = str(tmp_path / "logs")
    environment.update(overrides)

    result = subprocess.run(
        [sys.executable, "main.py", "--smoke-test"],
        cwd=Path(__file__).parents[1],
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_smoke_command_initializes_application_resources_and_logging(
    tmp_path: Path,
) -> None:
    environment = os.environ.copy()
    environment["QT_QPA_PLATFORM"] = "offscreen"
    environment["VIDEO_ANALYSE_LOG_DIR"] = str(tmp_path / "logs")

    result = subprocess.run(
        [sys.executable, "main.py", "--smoke-test"],
        cwd=Path(__file__).parents[1],
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["status"] == "ok"
    assert Path(report["font"]).is_file()
    assert Path(report["log"]) == tmp_path / "logs" / "video-analyse.log"
    assert Path(report["log"]).is_file()


def test_smoke_command_loads_a_qml_scene_and_renders_a_frame(tmp_path: Path) -> None:
    report = run_smoke_check(tmp_path)

    assert Path(report["qml"]).is_file()
    assert report["sceneRendered"] is True
    assert report["qmlWarnings"] == []
    assert report["renderingBackend"], "the report names no graphics backend"


def test_smoke_command_can_render_the_scene_in_software(tmp_path: Path) -> None:
    """The path an unmanaged device with a failing graphics driver falls to."""

    report = run_smoke_check(tmp_path, VIDEO_ANALYSE_SOFTWARE_RENDERING="1")

    assert report["sceneRendered"] is True
    assert report["renderingBackend"] == "software"


def test_smoke_command_writes_its_report_to_a_requested_file(tmp_path: Path) -> None:
    report_path = tmp_path / "smoke-report.json"
    environment = os.environ.copy()
    environment["QT_QPA_PLATFORM"] = "offscreen"
    environment["VIDEO_ANALYSE_LOG_DIR"] = str(tmp_path / "logs")
    environment["VIDEO_ANALYSE_SMOKE_REPORT"] = str(report_path)

    result = subprocess.run(
        [sys.executable, "main.py", "--smoke-test"],
        cwd=Path(__file__).parents[1],
        env=environment,
        capture_output=True,
        text=True,
        timeout=15,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(report_path.read_text(encoding="utf-8")) == json.loads(
        result.stdout
    )
