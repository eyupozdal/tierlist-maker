; Tier List Maker - Windows kurulum sihirbazı (Inno Setup)
#ifndef MyAppVersion
  #define MyAppVersion "1.0.0"
#endif

[Setup]
AppId={{B3C1F5A2-7D4E-4E8A-9F21-5A6C0D1E2F34}
AppName=Tier List Maker
AppVersion={#MyAppVersion}
AppVerName=Tier List Maker {#MyAppVersion}
AppPublisher=Tier List Maker
DefaultDirName={autopf}\Tier List Maker
DefaultGroupName=Tier List Maker
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=installer_output
OutputBaseFilename=TierListMaker-Setup
SetupIconFile=assets\icon.ico
UninstallDisplayIcon={app}\TierListMaker.exe
UninstallDisplayName=Tier List Maker
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"

[Tasks]
Name: "desktopicon"; Description: "Masaüstüne kısayol oluştur"; GroupDescription: "Ek görevler:"

[Files]
Source: "dist\TierListMaker\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Tier List Maker"; Filename: "{app}\TierListMaker.exe"
Name: "{autodesktop}\Tier List Maker"; Filename: "{app}\TierListMaker.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\TierListMaker.exe"; Description: "Tier List Maker'ı şimdi aç"; Flags: nowait postinstall skipifsilent
