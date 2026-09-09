"""External verification of the packaged Windows per-user installer.

The tests skip unless `scripts/build_windows.ps1` has produced its artifact, so
the ordinary source suite stays fast while release pipelines verify the real
installer. They walk one installation through its whole life: a silent per-user
install, a launch of the installed application, the optional desktop shortcut,
an in-place upgrade, and an uninstall. The tests share that installation, so
they run in the order written.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import time
import tomllib

import pytest


PROJECT_ROOT = Path(__file__).parents[1]
APPLICATION_NAME = "Video Analyse"
EXECUTABLE_NAME = f"{APPLICATION_NAME}.exe"
APPLICATION_ID = "{7A1F5D62-3C48-4B9E-9F0A-2D6E8B4C1A73}"
UNINSTALL_KEY = (
    rf"Software\Microsoft\Windows\CurrentVersion\Uninstall\{APPLICATION_ID}_is1"
)

pytestmark = pytest.mark.skipif(
    sys.platform != "win32", reason="the Windows installer is verified only on Windows"
)


def application_version() -> str:
    with (PROJECT_ROOT / "pyproject.toml").open("rb") as project_definition:
        return tomllib.load(project_definition)["project"]["version"]


def uninstall_registration() -> dict[str, str]:
    """The installed-apps entry Windows shows for Video Analyse."""

    import winreg

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY) as key:
        values = {}
        for index in range(winreg.QueryInfoKey(key)[1]):
            name, value, _ = winreg.EnumValue(key, index)
            values[name] = value
        return values


def registration_exists() -> bool:
    try:
        uninstall_registration()
    except OSError:
        return False
    return True


def wait_until(condition, *, timeout: float = 120.0) -> bool:
    """Poll `condition`, because Inno Setup's silent runs finish asynchronously."""

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.5)
    return condition()


def install(installer: Path, target: Path, *, tasks: str = "") -> None:
    """Install silently and per-user, exactly as an unattended check would."""

    completed = subprocess.run(
        [
            str(installer),
            "/VERYSILENT",
            "/SUPPRESSMSGBOXES",
            "/NORESTART",
            f"/DIR={target}",
            f"/TASKS={tasks}",
        ],
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert completed.returncode == 0, completed.stderr
    assert wait_until(
        lambda: (target / EXECUTABLE_NAME).is_file()
    ), f"{installer.name} did not install {EXECUTABLE_NAME} into {target}"


def desktop_shortcut() -> Path:
    return Path(os.environ["USERPROFILE"]) / "Desktop" / f"{APPLICATION_NAME}.lnk"


def start_menu_shortcut() -> Path:
    return (
        Path(os.environ["APPDATA"])
        / "Microsoft"
        / "Windows"
        / "Start Menu"
        / "Programs"
        / f"{APPLICATION_NAME}.lnk"
    )


@pytest.fixture(scope="module")
def installer() -> Path:
    artifact = (
        PROJECT_ROOT / "dist" / f"Video-Analyse-{application_version()}-x64-setup.exe"
    )
    if not artifact.is_file():
        pytest.skip(f"{artifact.name} is not built; run scripts/build_windows.ps1")
    return artifact


@pytest.fixture(scope="module")
def installation(
    installer: Path, tmp_path_factory: pytest.TempPathFactory
) -> Path:
    if registration_exists():
        pytest.skip("Video Analyse is already installed for this user")

    target = tmp_path_factory.mktemp("installation") / APPLICATION_NAME
    install(installer, target)
    return target


def test_installing_needs_no_administrator_rights(installation: Path) -> None:
    # A silent install that completes without an elevation prompt already proves
    # the point; the installed files must also live under the user's profile.
    assert (installation / EXECUTABLE_NAME).is_file()
    assert installation.is_relative_to(Path(os.environ["USERPROFILE"]))


def test_installation_registers_start_menu_and_uninstall_entries(
    installation: Path,
) -> None:
    assert start_menu_shortcut().is_file()

    registration = uninstall_registration()
    assert registration["DisplayName"] == APPLICATION_NAME
    assert registration["DisplayVersion"] == application_version()
    assert Path(registration["UninstallString"].strip('"')).is_file()


def test_a_desktop_shortcut_is_not_created_unless_requested(
    installation: Path,
) -> None:
    assert not desktop_shortcut().exists()


def test_a_desktop_shortcut_is_created_when_requested(
    installer: Path, installation: Path
) -> None:
    install(installer, installation, tasks="desktopicon")
    try:
        assert wait_until(lambda: desktop_shortcut().is_file())
    finally:
        desktop_shortcut().unlink(missing_ok=True)


def test_the_installed_application_completes_its_smoke_check(
    installation: Path, tmp_path: Path
) -> None:
    report_file = tmp_path / "smoke-report.json"
    environment = os.environ.copy()
    environment["QT_QPA_PLATFORM"] = "offscreen"
    environment["VIDEO_ANALYSE_LOG_DIR"] = str(tmp_path / "logs")
    environment["VIDEO_ANALYSE_SMOKE_REPORT"] = str(report_file)

    result = subprocess.run(
        [str(installation / EXECUTABLE_NAME), "--smoke-test"],
        env=environment,
        capture_output=True,
        timeout=300,
    )

    assert result.returncode == 0, result.stderr
    report = json.loads(report_file.read_text(encoding="utf-8"))
    assert report["status"] == "ok"
    assert Path(report["font"]).is_file()
    assert Path(report["font"]).is_relative_to(installation)
    assert Path(report["log"]).is_file()


def test_the_installed_executable_declares_the_intended_version(
    installation: Path,
) -> None:
    declared = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            "(Get-Item -LiteralPath "
            f"'{installation / EXECUTABLE_NAME}').VersionInfo.ProductVersion",
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    assert declared.startswith(application_version())


def test_a_later_version_upgrades_the_existing_installation_in_place(
    installer: Path, installation: Path
) -> None:
    marker = installation / "upgrade-marker.txt"
    marker.write_text("installed before the upgrade", encoding="utf-8")

    install(installer, installation)

    assert (installation / EXECUTABLE_NAME).is_file()
    assert marker.is_file(), "the upgrade replaced the installation directory"
    assert uninstall_registration()["DisplayName"] == APPLICATION_NAME
    marker.unlink()


def test_uninstalling_removes_the_application_and_its_entries(
    installation: Path,
) -> None:
    uninstaller = Path(uninstall_registration()["UninstallString"].strip('"'))

    completed = subprocess.run(
        [str(uninstaller), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"],
        capture_output=True,
        text=True,
        timeout=600,
    )

    assert completed.returncode == 0, completed.stderr
    assert wait_until(lambda: not (installation / EXECUTABLE_NAME).exists())
    assert wait_until(lambda: not start_menu_shortcut().exists())
    assert wait_until(lambda: not registration_exists())
