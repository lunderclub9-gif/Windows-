#define AppName "DocuMaker DZ"
#define AppVersion "0.1.2"
#define AppPublisher "DocuMaker DZ"
#define AppExeName "DocuMakerDZ.exe"

[Setup]
AppId={{A14CFA4B-75D9-4C9A-AC64-DF0D0A0D0D21}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\DocuMaker DZ
DefaultGroupName={#AppName}
OutputDir=..\installer-output
OutputBaseFilename=DocuMakerDZ-Setup-{#AppVersion}
SetupIconFile=..\documaker_dz\assets\icon.ico
UninstallDisplayIcon={app}\{#AppExeName}
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=lowest
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "arabic"; MessagesFile: "compiler:Languages\Arabic.isl"

[Tasks]
Name: "desktopicon"; Description: "إنشاء اختصار على سطح المكتب"; GroupDescription: "اختصارات إضافية:"; Flags: unchecked

[Files]
Source: "..\documaker_dz\dist\DocuMakerDZ.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\documaker_dz\assets\icon.ico"; DestDir: "{app}\assets"; Flags: ignoreversion
Source: "..\documaker_dz\bin\FFmpeg-LICENSE.txt"; DestDir: "{app}\licenses"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\assets\icon.ico"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\assets\icon.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "تشغيل DocuMaker DZ"; Flags: nowait postinstall skipifsilent
