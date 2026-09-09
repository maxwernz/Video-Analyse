#!/usr/bin/env bash
# Build the authoritative unsigned ARM64 macOS package for Video Analyse.
#
# The same command runs locally and in CI. It produces
# dist/Video-Analyse-<version>-arm64.dmg containing "Video Analyse.app",
# and fails if the packaged application cannot complete its smoke check.

set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"

application_name="Video Analyse"
bundle="dist/${application_name}.app"

if [[ "$(uname -s)" != "Darwin" || "$(uname -m)" != "arm64" ]]; then
    echo "This build must run natively on ARM64 macOS." >&2
    exit 1
fi

echo "==> Installing locked dependencies"
uv sync --locked --all-groups

version="$(uv run python -c 'import build_config.shared as s; print(s.application_version())')"
disk_image="dist/$(uv run python -c 'import build_config.shared as s; print(s.macos_disk_image_name())')"

echo "==> Building ${application_name} ${version} for arm64"
rm -rf build dist
uv run pyinstaller build_config/macos.spec --noconfirm --distpath dist --workpath build

if [[ ! -d "$bundle" ]]; then
    echo "PyInstaller did not produce ${bundle}." >&2
    exit 1
fi

echo "==> Verifying the ad-hoc signature"
codesign --verify --strict "$bundle"

# The smoke check deliberately uses no VIDEO_ANALYSE_LOG_DIR override so that the
# packaged application resolves its real operating-system diagnostic-log location.
echo "==> Running the packaged smoke check"
QT_QPA_PLATFORM=offscreen "${bundle}/Contents/MacOS/${application_name}" --smoke-test

echo "==> Creating ${disk_image}"
staging_directory="$(mktemp -d)"
cp -R "$bundle" "$staging_directory/"
ln -s /Applications "$staging_directory/Applications"
rm -f "$disk_image"
hdiutil create \
    -volname "$application_name" \
    -srcfolder "$staging_directory" \
    -fs HFS+ \
    -format UDZO \
    -quiet \
    "$disk_image"
rm -rf "$staging_directory"

echo "==> Built ${disk_image}"
