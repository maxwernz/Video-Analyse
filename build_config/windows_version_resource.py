"""The Windows version resource embedded in the packaged executable.

Windows reads an executable's semantic version from a compiled VERSIONINFO
resource rather than from any file name, so the resource is rendered from the
single project version instead of being maintained by hand.
"""

from __future__ import annotations

from pathlib import Path

from build_config.shared import APPLICATION_NAME, PUBLISHER, application_version


def _fixed_file_version(version: str) -> tuple[int, int, int, int]:
    """The four-part numeric version Windows requires for a semantic version."""

    parts = [int(part) for part in version.split(".")]
    if len(parts) != 3:
        raise ValueError(f"Expected a three-part semantic version, got {version!r}")
    return (parts[0], parts[1], parts[2], 0)


def render_version_resource() -> str:
    version = application_version()
    numbers = _fixed_file_version(version)

    return f"""VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={numbers},
    prodvers={numbers},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0),
  ),
  kids=[
    StringFileInfo([
      StringTable('040904B0', [
        StringStruct('CompanyName', '{PUBLISHER}'),
        StringStruct('FileDescription', '{APPLICATION_NAME}'),
        StringStruct('FileVersion', '{version}'),
        StringStruct('InternalName', '{APPLICATION_NAME}'),
        StringStruct('OriginalFilename', '{APPLICATION_NAME}.exe'),
        StringStruct('ProductName', '{APPLICATION_NAME}'),
        StringStruct('ProductVersion', '{version}'),
      ]),
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])]),
  ],
)
"""


def write_version_resource(directory: Path) -> Path:
    """Write the version resource into `directory` and return its path."""

    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / "windows_version_resource.txt"
    destination.write_text(render_version_resource(), encoding="utf-8")
    return destination
