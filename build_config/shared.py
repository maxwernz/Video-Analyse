"""Shared PyInstaller configuration for every Video Analyse platform package.

Platform specifications import this module so that application entry points,
dependencies, bundled resources, and metadata cannot drift between platforms.
"""

from __future__ import annotations

from pathlib import Path
import tomllib

from PyInstaller.utils.hooks import copy_metadata


APPLICATION_NAME = "Video Analyse"
BUNDLE_IDENTIFIER = "de.maxwernz.videoanalyse"
ARTIFACT_BASE_NAME = "Video-Analyse"
MACOS_ARCHITECTURE = "arm64"
PUBLISHER = "maxwernz"

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENTRY_SCRIPT = str(PROJECT_ROOT / "main.py")

HIDDEN_IMPORTS = ["moviepy"]

EXCLUDED_MODULES = [
    "QtDBus",
    "QtNetwork",
    "QtOpenGL",
    "QtPdf",
    "QtQml",
    "QtQmlMeta",
    "QtQmlModels",
    "QtQmlWorkerScript",
    "QtQuick",
    "QtSvg",
    "QtVirtualKeyboard",
    "PySide6.QtDBus",
]


def application_version() -> str:
    """The semantic version declared by the single project definition."""

    with (PROJECT_ROOT / "pyproject.toml").open("rb") as project_definition:
        return tomllib.load(project_definition)["project"]["version"]


def bundled_data() -> list[tuple[str, str]]:
    """Resources every packaged application must carry."""

    fonts = PROJECT_ROOT / "assets" / "fonts"
    return [
        (str(fonts / "NotoSans.ttf"), "assets/fonts"),
        (str(fonts / "OFL.txt"), "assets/fonts"),
    ] + copy_metadata("imageio")


def macos_disk_image_name() -> str:
    """The single authoritative filename of the macOS disk image."""

    return f"{ARTIFACT_BASE_NAME}-{application_version()}-{MACOS_ARCHITECTURE}.dmg"
