"""External verification of the packaged ARM64 macOS disk image.

The tests skip unless `scripts/build_macos.sh` has produced its artifact, so the
ordinary source suite stays fast while release pipelines verify the real package.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import plistlib
import subprocess
import sys
import tomllib

import pytest


PROJECT_ROOT = Path(__file__).parents[1]
APPLICATION_NAME = "Video Analyse"

pytestmark = pytest.mark.skipif(
    sys.platform != "darwin", reason="the macOS package is built only on macOS"
)


def application_version() -> str:
    with (PROJECT_ROOT / "pyproject.toml").open("rb") as project_definition:
        return tomllib.load(project_definition)["project"]["version"]


@pytest.fixture(scope="module")
def disk_image() -> Path:
    image = PROJECT_ROOT / "dist" / f"Video-Analyse-{application_version()}-arm64.dmg"
    if not image.is_file():
        pytest.skip(f"{image.name} is not built; run scripts/build_macos.sh")
    return image


@pytest.fixture(scope="module")
def mounted_application(disk_image: Path, tmp_path_factory: pytest.TempPathFactory):
    mount_point = tmp_path_factory.mktemp("mounted-disk-image")
    subprocess.run(
        ["hdiutil", "attach", str(disk_image), "-nobrowse", "-readonly",
         "-mountpoint", str(mount_point)],
        check=True,
        capture_output=True,
    )
    try:
        yield mount_point / f"{APPLICATION_NAME}.app"
    finally:
        subprocess.run(
            ["hdiutil", "detach", str(mount_point), "-quiet"], check=False
        )


def test_disk_image_contains_the_named_application(mounted_application: Path) -> None:
    assert mounted_application.is_dir()


def test_application_declares_its_identity_version_and_minimum_system(
    mounted_application: Path,
) -> None:
    metadata = plistlib.loads(
        (mounted_application / "Contents" / "Info.plist").read_bytes()
    )

    assert metadata["CFBundleIdentifier"] == "de.maxwernz.videoanalyse"
    assert metadata["CFBundleName"] == APPLICATION_NAME
    assert metadata["CFBundleShortVersionString"] == application_version()
    assert metadata["LSMinimumSystemVersion"] == "14.0"


def test_packaged_application_is_a_valid_arm64_bundle(
    mounted_application: Path,
) -> None:
    executable = mounted_application / "Contents" / "MacOS" / APPLICATION_NAME
    architectures = subprocess.run(
        ["lipo", "-archs", str(executable)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.split()

    assert architectures == ["arm64"]
    subprocess.run(
        ["codesign", "--verify", "--strict", str(mounted_application)], check=True
    )


def test_packaged_application_completes_its_smoke_check(
    mounted_application: Path, tmp_path: Path
) -> None:
    environment = os.environ.copy()
    environment["QT_QPA_PLATFORM"] = "offscreen"
    environment["VIDEO_ANALYSE_LOG_DIR"] = str(tmp_path / "logs")

    result = subprocess.run(
        [str(mounted_application / "Contents" / "MacOS" / APPLICATION_NAME),
         "--smoke-test"],
        env=environment,
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["status"] == "ok"
    assert Path(report["font"]).is_file()
    assert Path(report["font"]).is_relative_to(mounted_application)
    assert Path(report["log"]).is_file()
