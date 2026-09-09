; Per-user Windows installer for Video Analyse.
;
; Every value that build_config/shared.py owns arrives as a command-line define,
; so application metadata cannot drift between platforms. scripts/build_windows.ps1
; is the only supported caller:
;
;   ISCC /DApplicationName=... /DApplicationVersion=... /DPublisher=...
;        /DExecutableName=... /DOutputBaseFilename=... /DSourceDirectory=...
;        /DOutputDirectory=... /DIconFile=...
;
; The installer installs for the current user only, so Windows never asks for
; administrator elevation. AppId is a fixed GUID: it is the stable application
; identity that lets a later version upgrade an existing installation in place
; and keeps one entry in the installed-apps list across upgrades.
;
; Requires Inno Setup 6.3 or newer for the x64compatible architecture identifier.

#ifndef ApplicationName
  #error ApplicationName must be defined by the build script
#endif
#ifndef ApplicationVersion
  #error ApplicationVersion must be defined by the build script
#endif
#ifndef Publisher
  #error Publisher must be defined by the build script
#endif
#ifndef ExecutableName
  #error ExecutableName must be defined by the build script
#endif
#ifndef OutputBaseFilename
  #error OutputBaseFilename must be defined by the build script
#endif
#ifndef SourceDirectory
  #error SourceDirectory must be defined by the build script
#endif
#ifndef OutputDirectory
  #error OutputDirectory must be defined by the build script
#endif
#ifndef IconFile
  #error IconFile must be defined by the build script
#endif

[Setup]
AppId={{7A1F5D62-3C48-4B9E-9F0A-2D6E8B4C1A73}
AppName={#ApplicationName}
AppVersion={#ApplicationVersion}
AppVerName={#ApplicationName} {#ApplicationVersion}
AppPublisher={#Publisher}
VersionInfoVersion={#ApplicationVersion}
DefaultDirName={autopf}\{#ApplicationName}
DefaultGroupName={#ApplicationName}
DisableProgramGroupPage=yes
UsePreviousAppDir=yes
Uninstallable=yes
UninstallDisplayName={#ApplicationName}
UninstallDisplayIcon={app}\{#ExecutableName}
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.22000
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupIconFile={#IconFile}
OutputDir={#OutputDirectory}
OutputBaseFilename={#OutputBaseFilename}
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#SourceDirectory}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#ApplicationName}"; Filename: "{app}\{#ExecutableName}"
Name: "{autodesktop}\{#ApplicationName}"; Filename: "{app}\{#ExecutableName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#ExecutableName}"; Description: "{cm:LaunchProgram,{#ApplicationName}}"; Flags: nowait postinstall skipifsilent
