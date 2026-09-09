"""Verification of the Windows packaging contract that needs no Windows host.

These checks run on every platform so that a macOS developer cannot silently
break the Windows installer's promises: per-user installation, a stable
application identity across upgrades, an optional desktop shortcut, and one
semantic version shared by the executable and the installer.

The behaviour of a real installation is verified separately by
`tests/test_windows_package.py`, which runs only on Windows.
"""

from __future__ import annotations

from pathlib import Path
import re
import tomllib

import pytest


PROJECT_ROOT = Path(__file__).parents[1]
INSTALLER_SCRIPT = PROJECT_ROOT / "build_config" / "windows_installer.iss"
SPEC = PROJECT_ROOT / "build_config" / "windows.spec"
BUILD_SCRIPT = PROJECT_ROOT / "scripts" / "build_windows.ps1"


def application_version() -> str:
    with (PROJECT_ROOT / "pyproject.toml").open("rb") as project_definition:
        return tomllib.load(project_definition)["project"]["version"]


@pytest.fixture(scope="module")
def installer_script() -> str:
    return INSTALLER_SCRIPT.read_text(encoding="utf-8")


def directive(installer_script: str, name: str) -> str:
    match = re.search(rf"^{name}=(.*)$", installer_script, re.MULTILINE)
    assert match is not None, f"{name} is not declared in {INSTALLER_SCRIPT.name}"
    return match.group(1).strip()


def test_installation_never_requests_administrator_elevation(
    installer_script: str,
) -> None:
    assert directive(installer_script, "PrivilegesRequired") == "lowest"
    assert directive(installer_script, "DefaultDirName").startswith("{autopf}")


def test_installation_targets_windows_x64(installer_script: str) -> None:
    assert directive(installer_script, "ArchitecturesAllowed") == "x64compatible"
    assert (
        directive(installer_script, "ArchitecturesInstallIn64BitMode")
        == "x64compatible"
    )


def test_upgrades_reuse_a_stable_application_identity(installer_script: str) -> None:
    application_id = directive(installer_script, "AppId")

    assert re.fullmatch(
        r"\{\{[0-9A-Fa-f-]{36}\}", application_id
    ), f"AppId must be a fixed GUID, not {application_id!r}"
    assert directive(installer_script, "UsePreviousAppDir") == "yes"


def test_start_menu_and_uninstall_entries_are_always_created(
    installer_script: str,
) -> None:
    assert "{autoprograms}\\{#ApplicationName}" in installer_script
    assert directive(installer_script, "Uninstallable") != "no"


def test_a_desktop_shortcut_is_offered_but_not_preselected(
    installer_script: str,
) -> None:
    desktop_task = re.search(
        r'^Name: "desktopicon";.*$', installer_script, re.MULTILINE
    )
    assert desktop_task is not None, "the installer offers no desktop shortcut task"
    assert "unchecked" in desktop_task.group(0)

    desktop_icon = re.search(r"^Name: \"\{autodesktop\}.*$", installer_script, re.MULTILINE)
    assert desktop_icon is not None, "no desktop shortcut is defined"
    assert "Tasks: desktopicon" in desktop_icon.group(0)


def test_the_installer_carries_the_declared_semantic_version(
    installer_script: str,
) -> None:
    from build_config.shared import artifact_name

    assert directive(installer_script, "AppVersion") == "{#ApplicationVersion}"
    assert directive(installer_script, "VersionInfoVersion") == "{#ApplicationVersion}"
    assert directive(installer_script, "OutputBaseFilename") == "{#OutputBaseFilename}"
    assert (
        artifact_name("x64-setup")
        == f"Video-Analyse-{application_version()}-x64-setup"
    )


def test_the_build_script_supplies_every_value_the_installer_requires(
    installer_script: str,
) -> None:
    """Nothing the installer needs may be restated inside the installer script."""

    required_defines = set(re.findall(r"^#ifndef (\w+)$", installer_script, re.MULTILINE))
    assert required_defines, "the installer script declares no required defines"

    build_script = BUILD_SCRIPT.read_text(encoding="utf-8")
    supplied = set(re.findall(r"/D(\w+)=", build_script))

    assert required_defines <= supplied, (
        "the build script never supplies "
        f"{sorted(required_defines - supplied)}"
    )


def test_the_installer_reuses_the_shared_application_metadata() -> None:
    build_script = BUILD_SCRIPT.read_text(encoding="utf-8")

    assert "import build_config.shared as shared" in build_script
    for shared_name in (
        "shared.APPLICATION_NAME",
        "shared.PUBLISHER",
        "shared.application_version()",
        "shared.artifact_name(",
    ):
        assert shared_name in build_script, f"the build script does not reuse {shared_name}"


def test_windows_packaging_reuses_the_shared_configuration() -> None:
    spec = SPEC.read_text(encoding="utf-8")

    for shared_name in (
        "APPLICATION_NAME",
        "ENTRY_SCRIPT",
        "EXCLUDED_MODULES",
        "HIDDEN_IMPORTS",
        "bundled_data",
        "write_version_resource",
    ):
        assert shared_name in spec, f"windows.spec does not reuse {shared_name}"


def test_the_windows_executable_declares_the_project_version() -> None:
    from build_config.windows_version_resource import render_version_resource

    resource = render_version_resource()
    version = application_version()
    numbers = tuple(int(part) for part in version.split("."))

    assert f"filevers={numbers + (0,)}" in resource
    assert f"StringStruct('FileVersion', '{version}')" in resource
    assert f"StringStruct('ProductVersion', '{version}')" in resource
    assert "StringStruct('ProductName', 'Video Analyse')" in resource


def test_one_documented_command_builds_the_windows_artifact() -> None:
    assert BUILD_SCRIPT.is_file()
    build_script = BUILD_SCRIPT.read_text(encoding="utf-8")

    assert "uv sync --locked --all-groups" in build_script
    assert "build_config/windows.spec" in build_script
    assert "--smoke-test" in build_script
    assert "windows_installer.iss" in build_script
    # The compiler's own build of the x64compatible installer is the capability
    # check. Some valid Inno Setup builds expose neither useful version metadata
    # nor a version command, so the build script must not reject them preflight.
    assert "VersionInfo" not in build_script
    assert "--version" not in build_script

    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    assert "scripts/build_windows.ps1" in readme
