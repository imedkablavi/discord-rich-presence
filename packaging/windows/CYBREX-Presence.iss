#ifndef AppVersion
  #define AppVersion "0.0.0-dev"
#endif

#define AppName "CYBREX Presence"
#define AppPublisher "CYBREX@TECH"
#define AppURL "https://github.com/imedkablavi/discord-rich-presence"
#define AppExeName "DiscordRichPresence.exe"

[Setup]
AppId={{D82E6D0D-9D16-41E7-B480-E70E68D70AF6}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}/issues
AppUpdatesURL={#AppURL}/releases/latest
DefaultDirName={localappdata}\Programs\CYBREX Presence
DefaultGroupName=CYBREX Presence
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..\..\dist
OutputBaseFilename=CYBREX-Presence-Setup
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
UninstallDisplayName=CYBREX Presence
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
RestartApplications=no
SetupLogging=yes

[Files]
Source: "..\..\dist\DiscordRichPresence.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\CYBREX Presence"; Filename: "{app}\{#AppExeName}"; Parameters: "--gui"; WorkingDir: "{app}"
Name: "{userdesktop}\CYBREX Presence"; Filename: "{app}\{#AppExeName}"; Parameters: "--gui"; WorkingDir: "{app}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Run]
Filename: "{app}\{#AppExeName}"; Parameters: "--gui"; Description: "Launch CYBREX Presence"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{app}\{#AppExeName}"; Parameters: "--shutdown"; Flags: runhidden waituntilterminated; RunOnceId: "StopCYBREXPresence"
