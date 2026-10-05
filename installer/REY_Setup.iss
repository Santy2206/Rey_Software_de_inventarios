; =====================================================================
; REY Inventarios - Instalador para Windows (Inno Setup 6)
; Genera REY_Setup.exe que instala PostgreSQL (si falta), la app,
; la base de datos, los accesos directos y el desinstalador.
; =====================================================================

#define MyAppName "REY Inventarios"
#define MyAppVersion "2.0"
#define MyAppPublisher "SENA ADSO Ficha 3186627"
#define MyAppURL "https://github.com/Santy2206/Rey_Software_de_inventarios"
#define MyAppExeName "REY_Inventarios.exe"
#define MyAppId "b7788dfa-1643-401f-a903-e3807e7df895"

[Setup]
AppId={{{#MyAppId}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={autopf}\REY Inventarios
DisableProgramGroupPage=yes
PrivilegesRequired=admin
OutputDir=..\dist
OutputBaseFilename=REY_Setup
SetupIconFile=..\assets\icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
CloseApplications=force

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Files]
; Ejecutable y dependencias empaquetados con PyInstaller/flet pack
Source: "source\REY_Inventarios\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "source\REY_Inventarios\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs

; Scripts de base de datos
Source: "..\deploy\db\01_schema.sql"; DestDir: "{app}\base_de_datos"; Flags: ignoreversion
Source: "..\deploy\db\02_seed.sql";   DestDir: "{app}\base_de_datos"; Flags: ignoreversion
Source: "source\crear_bd.bat";                 DestDir: "{app}"; Flags: ignoreversion

; Configuracion inicial (.env) - solo si no existe ya
Source: "source\env.ejemplo"; DestDir: "{app}"; DestName: ".env"; Flags: onlyifdoesntexist

; Instalador de PostgreSQL (se ejecuta solo si falta o si se fuerza reinstalacion)
Source: "source\postgresql-win-x64.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall

[Icons]
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autoprograms}\{#MyAppName}\Desinstalar {#MyAppName}"; Filename: "{uninstallexe}"

[Run]
; Desinstala PostgreSQL existente si se fuerza reinstalacion
Filename: "{code:PostgreSQLUninstallerPath|x}"; \
  Parameters: "/S"; \
  Description: "Desinstalando PostgreSQL existente"; \
  StatusMsg: "Desinstalando PostgreSQL existente..."; \
  Check: NeedsPostgreSQLUninstall

; Instala PostgreSQL en silencio si no esta presente o se forzo reinstalacion
Filename: "{tmp}\postgresql-win-x64.exe"; \
  Parameters: "--mode unattended --unattendedmodeui minimal --superpassword UDMVnxjZVgDT --serverport 5432"; \
  Description: "Instalando PostgreSQL"; \
  StatusMsg: "Instalando PostgreSQL (puede tardar varios minutos)..."; \
  Check: NeedsPostgreSQLInstall

; Crea usuario, base de datos, tablas y datos iniciales
Filename: "{app}\crear_bd.bat"; \
  Parameters: "{code:PostgresPassword|UDMVnxjZVgDT}"; \
  Description: "Configurando base de datos"; \
  StatusMsg: "Creando usuario, base de datos y tablas..."

; Ofrece abrir REY al finalizar
Filename: "{app}\{#MyAppExeName}"; \
  Description: "Abrir {#MyAppName}"; \
  Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\*"

[Code]
var
  PostgresPassPage: TInputQueryWizardPage;
  PostgresPassAttempts: Integer;
  ForceReinstallPostgreSQL: Boolean;

function PostgreSQLPath: string;
var
  Versions: array of String;
  i: Integer;
  Path: string;
begin
  Versions := ['18', '17', '16', '15', '14'];
  for i := 0 to GetArrayLength(Versions) - 1 do
  begin
    Path := ExpandConstant('{pf64}\PostgreSQL\' + Versions[i] + '\bin\psql.exe');
    if FileExists(Path) then
    begin
      Result := Path;
      Exit;
    end;
    Path := ExpandConstant('{pf}\PostgreSQL\' + Versions[i] + '\bin\psql.exe');
    if FileExists(Path) then
    begin
      Result := Path;
      Exit;
    end;
  end;
  Result := '';
end;

function PostgreSQLUninstallerPath(Param: string): string;
var
  Versions: array of String;
  i: Integer;
  Path: string;
begin
  Versions := ['18', '17', '16', '15', '14'];
  for i := 0 to GetArrayLength(Versions) - 1 do
  begin
    Path := ExpandConstant('{pf64}\PostgreSQL\' + Versions[i] + '\uninstall-postgresql.exe');
    if FileExists(Path) then
    begin
      Result := Path;
      Exit;
    end;
    Path := ExpandConstant('{pf}\PostgreSQL\' + Versions[i] + '\uninstall-postgresql.exe');
    if FileExists(Path) then
    begin
      Result := Path;
      Exit;
    end;
  end;
  Result := '';
end;

function NeedsPostgreSQLInstall: Boolean;
begin
  Result := ForceReinstallPostgreSQL or (PostgreSQLPath = '');
end;

function NeedsPostgreSQLUninstall: Boolean;
begin
  Result := ForceReinstallPostgreSQL and (PostgreSQLUninstallerPath('') <> '');
end;

function TestPostgresPassword(Pass: string): Boolean;
var
  psql: string;
  ExitCode: Integer;
  CmdLine: string;
begin
  psql := PostgreSQLPath;
  if psql = '' then
  begin
    Result := False;
    Exit;
  end;
  CmdLine := '/c set "PGPASSWORD=' + Pass + '" && "' + psql + '" -h localhost -U postgres -c "SELECT 1"';
  if Exec(ExpandConstant('{sys}\cmd.exe'), CmdLine, '', SW_HIDE, ewWaitUntilTerminated, ExitCode) then
    Result := ExitCode = 0
  else
    Result := False;
end;

procedure InitializeWizard;
begin
  PostgresPassAttempts := 0;
  ForceReinstallPostgreSQL := False;
  if not NeedsPostgreSQLInstall then
  begin
    PostgresPassPage := CreateInputQueryPage(wpSelectDir,
      'Contrasena de PostgreSQL',
      'PostgreSQL ya esta instalado en este equipo',
      'Para crear o actualizar la base de datos rey_inventarios, ingrese la contrasena del usuario postgres. Si la deja vacia se intentara con la contrasena por defecto de REY (UDMVnxjZVgDT).');
    PostgresPassPage.Add('Contrasena de postgres:', True);
  end;
end;

function PostgresPassword(Param: string): string;
begin
  if ForceReinstallPostgreSQL then
    Result := 'UDMVnxjZVgDT'
  else if Assigned(PostgresPassPage) then
  begin
    Result := PostgresPassPage.Values[0];
    if Result = '' then
      Result := 'UDMVnxjZVgDT';
  end
  else
    Result := 'UDMVnxjZVgDT';
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if Assigned(PostgresPassPage) and (CurPageID = PostgresPassPage.ID) then
  begin
    PostgresPassAttempts := PostgresPassAttempts + 1;
    if not TestPostgresPassword(PostgresPassPage.Values[0]) then
    begin
      if PostgresPassAttempts >= 3 then
      begin
        if MsgBox('La contrasena de postgres es incorrecta.' #13#10 #13#10 +
          'REY puede reinstalar PostgreSQL con la contrasena por defecto UDMVnxjZVgDT.' #13#10 +
          'ATENCION: esto borrara TODAS las bases de datos existentes en este equipo.' #13#10 #13#10 +
          'Desea continuar con la reinstalacion automatica?', mbConfirmation, MB_YESNO) = IDYES then
        begin
          ForceReinstallPostgreSQL := True;
        end
        else
        begin
          Result := False;
        end;
      end
      else
      begin
        MsgBox('Contrasena incorrecta. Intento ' + IntToStr(PostgresPassAttempts) + ' de 3.' #13#10 +
          'Escriba la contrasena correcta o deje que REY reinstale PostgreSQL tras el tercer intento.', mbError, MB_OK);
        Result := False;
      end;
    end;
  end;
end;
