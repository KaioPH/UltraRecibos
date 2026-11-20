; ============================================
; ULTRA RECIBOS - INSTALADOR WINDOWS
; Versao 2.5.1
; Desenvolvedor: Kaio Phyllipe Rodrigues
; ============================================
; Gere primeiro o executavel com build_windows.bat
; (PyInstaller -> pasta dist\UltraRecibos).
;
; IMPORTANTE: o AppId deve permanecer o mesmo das versoes
; anteriores para que a instalacao funcione como atualizacao.
;
; Os dados (banco, PDFs, backups) ficam em
; %LOCALAPPDATA%\UltraRecibos e NAO sao removidos na
; atualizacao nem na desinstalacao.

#define MyAppVersion "2.5.1"

[Setup]
AppId=UltraRecibos.KaioPhyllipeRodrigues
AppName=Ultra Recibos
AppVersion={#MyAppVersion}
AppVerName=Ultra Recibos {#MyAppVersion}
AppPublisher=Kaio Phyllipe Rodrigues
VersionInfoVersion={#MyAppVersion}.0
VersionInfoCompany=Kaio Phyllipe Rodrigues
VersionInfoDescription=Instalador Ultra Recibos
VersionInfoProductName=Ultra Recibos
VersionInfoProductVersion={#MyAppVersion}

DefaultDirName={autopf}\Ultra Recibos
DefaultGroupName=Ultra Recibos
DisableProgramGroupPage=yes

OutputDir=instalador
OutputBaseFilename=UltraRecibos_Setup_{#MyAppVersion}

SetupIconFile=assets\ultra_recibos.ico
UninstallDisplayIcon={app}\UltraRecibos.exe
UninstallDisplayName=Ultra Recibos {#MyAppVersion}

Compression=lzma2
SolidCompression=yes
WizardStyle=modern

PrivilegesRequired=admin
MinVersion=10.0
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

CloseApplications=yes
RestartApplications=no

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na area de trabalho"; GroupDescription: "Atalhos:"; Flags: unchecked

[InstallDelete]
; Remove bibliotecas da versao anterior antes de copiar as novas
; (evita arquivos antigos misturados apos troca de versao do Python).
; Apenas a pasta do programa; os dados do usuario nao sao afetados.
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "dist\UltraRecibos\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Ultra Recibos"; Filename: "{app}\UltraRecibos.exe"
Name: "{autodesktop}\Ultra Recibos"; Filename: "{app}\UltraRecibos.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\UltraRecibos.exe"; Description: "Executar Ultra Recibos"; Flags: nowait postinstall skipifsilent
