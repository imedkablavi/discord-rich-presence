#define MyAppName "Discord Rich Presence"
#ifndef MyAppVersion
  #define MyAppVersion "2.1.0"
#endif
#define MyAppPublisher "imedkablavi"
#define MyAppExeName "DiscordRichPresence.exe"

[Setup]
AppId={{A63A8D54-2B2F-4A18-A8A8-89A6B00A0F5A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\Discord Rich Presence
DefaultGroupName={#MyAppName}
OutputDir=..\..\release-dist
OutputBaseFilename=DiscordRichPresence-Setup-{#MyAppVersion}-windows-x86_64
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
CloseApplications=yes
RestartApplications=no

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked
Name: "startup"; Description: "Start Discord Rich Presence when I sign in"; GroupDescription: "Startup:"; Flags: unchecked

[Files]
Source: "..\..\dist\DiscordRichPresence.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\config.example.yaml"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Discord Rich Presence"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--gui"
Name: "{autodesktop}\Discord Rich Presence"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--gui"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "DiscordRichPresence"; ValueData: """{app}\{#MyAppExeName}"" --tray"; Flags: uninsdeletevalue; Tasks: startup

[Run]
Filename: "{app}\{#MyAppExeName}"; Parameters: "--gui"; Description: "Open Discord Rich Presence"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{app}\{#MyAppExeName}"; Parameters: "--stop-service"; Flags: runhidden waituntilterminated skipifdoesntexist

[Code]
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then
    RegDeleteValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Run', 'DiscordRichPresence');
end;
