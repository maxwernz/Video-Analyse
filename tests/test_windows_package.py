"""External verification of the packaged Windows per-user installer.

The tests walk one installation through its whole life: a silent per-user
install into the location the installer chooses itself, a launch of the
installed application, the optional desktop shortcut, an upgrade by a genuinely
later version, and an uninstall. They share that installation, so they run in
the order written.

They skip unless `scripts/build_windows.ps1` has produced its artifact, so the
ordinary source suite stays fast. Set `VIDEO_ANALYSE_REQUIRE_PACKAGE=1` — as the
release pipeline does — to turn those skips into failures, so a pipeline cannot
report success for a verification that never ran.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

import pytest

from build_config.shared import (
    APPLICATION_NAME,
    PUBLISHER,
    application_version,
    artifact_name,
)


PROJECT_ROOT = Path(__file__).parents[1]
EXECUTABLE_NAME = f"{APPLICATION_NAME}.exe"
APPLICATION_ID = "{7A1F5D62-3C48-4B9E-9F0A-2D6E8B4C1A73}"
UNINSTALL_KEY = (
    rf"Software\Microsoft\Windows\CurrentVersion\Uninstall\{APPLICATION_ID}_is1"
)
UPGRADE_VERSION = "99.0.0"

pytestmark = pytest.mark.skipif(
    sys.platform != "win32", reason="the Windows installer is verified only on Windows"
)


def unavailable(reason: str) -> None:
    """Skip, unless the caller demanded that this verification actually run."""

    if os.environ.get("VIDEO_ANALYSE_REQUIRE_PACKAGE") == "1":
        pytest.fail(f"VIDEO_ANALYSE_REQUIRE_PACKAGE is set but {reason}")
    pytest.skip(reason)


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


def install(installer: Path, *, tasks: str = "") -> Path:
    """Install silently and per-user, letting the installer choose its location.

    No `/DIR` is passed, so the installation exercises the installer's own
    per-user `DefaultDirName` rather than a directory the test picked.
    """

    completed = subprocess.run(
        [
            str(installer),
            "/VERYSILENT",
            "/SUPPRESSMSGBOXES",
            "/NORESTART",
            f"/TASKS={tasks}",
        ],
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert completed.returncode == 0, completed.stderr
    assert wait_until(registration_exists), f"{installer.name} registered no installation"

    location = Path(uninstall_registration()["InstallLocation"])
    assert wait_until(
        lambda: (location / EXECUTABLE_NAME).is_file()
    ), f"{installer.name} did not install {EXECUTABLE_NAME} into {location}"
    return location


def inno_setup_compiler() -> Path:
    on_path = shutil.which("ISCC.exe")
    if on_path:
        return Path(on_path)

    for program_files in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)")):
        if not program_files:
            continue
        candidate = Path(program_files) / "Inno Setup 6" / "ISCC.exe"
        if candidate.is_file():
            return candidate

    unavailable("Inno Setup (ISCC.exe) is not installed")
    raise AssertionError("unreachable")


def build_upgrade_installer(destination: Path) -> Path:
    """Compile the same application as a later version, to test a real upgrade."""

    packaged_application = PROJECT_ROOT / "dist" / APPLICATION_NAME
    if not packaged_application.is_dir():
        unavailable(f"{packaged_application} is not built; run scripts/build_windows.ps1")

    output_base_name = f"Video-Analyse-{UPGRADE_VERSION}-x64-setup"
    subprocess.run(
        [
            str(inno_setup_compiler()),
            f"/DApplicationName={APPLICATION_NAME}",
            f"/DApplicationVersion={UPGRADE_VERSION}",
            f"/DPublisher={PUBLISHER}",
            f"/DExecutableName={EXECUTABLE_NAME}",
            f"/DOutputBaseFilename={output_base_name}",
            f"/DSourceDirectory={packaged_application}",
            f"/DOutputDirectory={destination}",
            f"/DIconFile={PROJECT_ROOT / 'icons' / 'app_icon.ico'}",
            str(PROJECT_ROOT / "build_config" / "windows_installer.iss"),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=900,
    )
    return destination / f"{output_base_name}.exe"


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
    artifact = PROJECT_ROOT / "dist" / f"{artifact_name('x64-setup')}.exe"
    if not artifact.is_file():
        unavailable(f"{artifact.name} is not built; run scripts/build_windows.ps1")
    return artifact


@pytest.fixture(scope="module")
def installation(installer: Path) -> Path:
    if registration_exists():
        unavailable("Video Analyse is already installed for this user")
    return install(installer)


def test_installing_needs_no_administrator_rights(installation: Path) -> None:
    # A silent install that completes without an elevation prompt already proves
    # the point; the chosen location must also be the current user's own, which
    # is what lets the install succeed unelevated.
    per_user_programs = Path(os.environ["LOCALAPPDATA"]).resolve() / "Programs"

    assert (installation / EXECUTABLE_NAME).is_file()
    assert installation.resolve().is_relative_to(per_user_programs)


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
    install(installer, tasks="desktopicon")
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
    assert Path(report["font"]).resolve().is_relative_to(installation.resolve())
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
    installation: Path, tmp_path: Path
) -> None:
    marker = installation / "upgrade-marker.txt"
    marker.write_text("installed before the upgrade", encoding="utf-8")

    upgraded_location = install(build_upgrade_installer(tmp_path))

    assert upgraded_location.resolve() == installation.resolve()
    assert marker.is_file(), "the upgrade replaced the installation directory"
    assert (installation / EXECUTABLE_NAME).is_file()

    registration = uninstall_registration()
    assert registration["DisplayName"] == APPLICATION_NAME, (
        "the upgrade did not retain the stable application identity"
    )
    assert registration["DisplayVersion"] == UPGRADE_VERSION
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
