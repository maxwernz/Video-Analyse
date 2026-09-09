import json
import os
from pathlib import Path
import subprocess
import sys


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
        timeout=15,
    )

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["status"] == "ok"
    assert Path(report["font"]).is_file()
    assert Path(report["log"]) == tmp_path / "logs" / "video-analyse.log"
    assert Path(report["log"]).is_file()
