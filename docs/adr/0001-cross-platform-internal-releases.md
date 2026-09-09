# Automate cross-platform internal releases

Video Analyse publishes immutable semantic-version releases from Git tags through GitHub Actions. Native GitHub-hosted runners build an ARM64 macOS 14+ DMG and a Windows 11 x64 per-user installer from platform-specific PyInstaller specifications that share common configuration; a draft GitHub Release becomes public only after both builds and their smoke checks pass. Published artifacts are unsigned, so each platform's first-launch security instructions are part of the release, and later fixes receive a new patch version rather than replacing existing artifacts.

## Consequences

- The first formal release is `v0.1.0`, and CI-produced artifacts are authoritative.
- Pull requests run tests and packaging smoke checks; tags additionally publish releases.
- `pyproject.toml` and committed lock data are the dependency source of truth, and local builds use the same entry points as CI.
- The application identity is `de.maxwernz.videoanalyse`, with the visible name `Video Analyse`.
- The Windows installer is per-user, requires no administrator rights, upgrades in place, creates Start Menu and uninstall entries, and makes a desktop shortcut optional.
- Automatic updates, paid signing, notarization, and self-hosted runners are outside the initial release scope.
- Published artifacts are never silently replaced; a defective release is marked accordingly and followed by a patch release.

Runtime portability uses cross-platform Qt or Python facilities by default. A platform adapter is introduced only for a capability whose behavior genuinely differs between macOS and Windows; speculative `MacOSAdapter` and `WindowsAdapter` collections are avoided. The application bundles a redistributable font for consistent exports, supports a non-interactive packaged smoke-test mode, and writes local-only diagnostics to the operating system's standard application-data directory.
