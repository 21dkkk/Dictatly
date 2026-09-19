; Dictatly Inno Setup Script
; Generates a clean, modern Windows installer for Dictatly with bundled Faster-Whisper models.

#ifndef AppVersion
#define AppVersion "1.1.1"
#endif

[Setup]
AppId={{D9A3B580-21D7-4B31-B488-875CD8A1B022}
AppName=Dictatly
AppVersion={#AppVersion}
AppVerName=Dictatly {#AppVersion}
AppPublisher=Dictatly
AppPublisherURL=https://github.com/21dkkk/Dictatly
AppSupportURL=https://github.com/21dkkk/Dictatly/issues
AppUpdatesURL=https://github.com/21dkkk/Dictatly/releases
DefaultDirName={autopf}\Dictatly
DefaultGroupName=Dictatly
DisableProgramGroupPage=yes
LicenseFile=..\LICENSE
OutputDir=..\dist\installer
OutputBaseFilename=Dictatly-Setup
SetupIconFile=..\resources\app_icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog commandline
UninstallDisplayIcon={app}\Dictatly.exe
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "startupicon"; Description: "Запускать Dictatly при входе в Windows / Start Dictatly on Windows startup"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\Dictatly\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Dictatly"; Filename: "{app}\Dictatly.exe"; IconFilename: "{app}\resources\app_icon.ico"
Name: "{autodesktop}\Dictatly"; Filename: "{app}\Dictatly.exe"; IconFilename: "{app}\resources\app_icon.ico"; Tasks: desktopicon
Name: "{userstartup}\Dictatly"; Filename: "{app}\Dictatly.exe"; IconFilename: "{app}\resources\app_icon.ico"; Tasks: startupicon

[Run]
Filename: "{app}\Dictatly.exe"; Description: "{cm:LaunchProgram,Dictatly}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\models"
