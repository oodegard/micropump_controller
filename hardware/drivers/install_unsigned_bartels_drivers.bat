

@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM ===================== Optional Dry Run Mode =====================
REM Set DRY_RUN=1 to echo destructive commands instead of executing them.
if defined DRY_RUN (
  set "RUN=echo [DRY-RUN] "
  echo DRY_RUN enabled: destructive actions will be echoed only.
  set "SKIP_UAC=1"
) else (
  set "RUN="
)

:: BatchGotAdmin
:-------------------------------------
REM  --> Check for permissions
if defined SKIP_UAC goto gotAdmin
IF "%PROCESSOR_ARCHITECTURE%" EQU "amd64" (
>nul 2>&1 "%SYSTEMROOT%\SysWOW64\cacls.exe" "%SYSTEMROOT%\SysWOW64\config\system"
) ELSE (
>nul 2>&1 "%SYSTEMROOT%\system32\cacls.exe" "%SYSTEMROOT%\system32\config\system"
)

REM --> If error flag set, we do not have admin.
if '%errorlevel%' NEQ '0' (
  echo Requesting administrative privileges...
  goto UACPrompt
) else ( goto gotAdmin )

:UACPrompt
  echo Set UAC = CreateObject^("Shell.Application"^) > "%temp%\getadmin.vbs"
  set params= %*
  echo UAC.ShellExecute "cmd.exe", "/c ""%~s0"" %params:"=""%", "", "runas", 1 >> "%temp%\getadmin.vbs"

  "%temp%\getadmin.vbs"
  del "%temp%\getadmin.vbs"

  exit /B

:gotAdmin
  pushd "%CD%"
  CD /D "%~dp0"
:--------------------------------------

:: ===================== Extract Bartels Driver ZIP if present =====================
set "ZIP_FILE=Bartels_controller_XU7_USB_Driver_2.08.30_uncert.zip"
set "TEMP_DIR=%TEMP%\DriverInstallUnsigned"
if exist "%TEMP_DIR%" rmdir /s /q "%TEMP_DIR%"
mkdir "%TEMP_DIR%"
if exist "%~dp0%ZIP_FILE%" (
  echo Extracting %ZIP_FILE% to %TEMP_DIR% ...
  powershell -Command "Expand-Archive -Path \"%~dp0%ZIP_FILE%\" -DestinationPath \"%TEMP_DIR%\" -Force"
  echo Extraction complete.
  REM Keep window open at the end for error review
)

if defined DRY_RUN echo DEBUG: after unzip


:: ===================== Admin Elevation (BatchGotAdmin) =====================
:: Your snippet with tiny tweaks
IF defined SKIP_UAC goto GotAdmin
IF "%PROCESSOR_ARCHITECTURE%" EQU "amd64" (
  >nul 2>&1 "%SYSTEMROOT%\SysWOW64\cacls.exe" "%SYSTEMROOT%\SysWOW64\config\system"
) ELSE (
  >nul 2>&1 "%SYSTEMROOT%\system32\cacls.exe" "%SYSTEMROOT%\system32\config\system"
)

if '%errorlevel%' NEQ '0' (
  echo Requesting administrative privileges...
  goto UACPrompt
) else (
  goto GotAdmin
)

:UACPrompt
  echo Set UAC = CreateObject^("Shell.Application"^) > "%temp%\getadmin.vbs"
  set params=%*
  echo UAC.ShellExecute "cmd.exe", "/c ""%~s0"" %params:"=""%", "", "runas", 1 >> "%temp%\getadmin.vbs"
  "%temp%\getadmin.vbs"
  del "%temp%\getadmin.vbs"
  exit /B

:GotAdmin
pushd "%CD%"
cd /D "%~dp0"
if defined DRY_RUN echo DEBUG: at GotAdmin 2

:: ===================== Args & Prompt =====================
:: Usage:  Install_Bartels_Unsigned_Driver.bat "C:\path\to\bartels.inf" [/NOSUBDIRS]

set "INF=%~1"
set "SUBDIRS=1"
if /I "%~2"==" /NOSUBDIRS" set "SUBDIRS=0"
if /I "%~2"=="/NOSUBDIRS" set "SUBDIRS=0"
if defined DRY_RUN echo DEBUG: args parsed

:: If no INF provided, try to find one in the extracted temp dir
REM Use a helper label to avoid nested parentheses issues with ECHO ON
if defined DRY_RUN echo DEBUG: before AutoFindINF
if not defined INF call :AutoFindINF
if defined DRY_RUN echo DEBUG: after AutoFindINF, INF="%INF%"

if defined INF goto :SkipINFPrompt
echo.
echo Enter FULL path to the driver .INF (you can also drag the .INF onto this .bat next time):
set /p INF=INF Path: 
:SkipINFPrompt

if defined DRY_RUN echo DEBUG: before INF existence check
if not defined INF (
  echo No INF provided. Exiting.
  pause
  goto :EOF
)

if not exist "%INF%" (
  echo File not found: "%INF%"
  echo.
  echo Press any key to exit...
  pause >nul
  goto :EOF
)

if defined DRY_RUN echo DEBUG: after INF existence check

for %%I in ("%INF%") do set "INF=%%~fI"

:: ===================== Paths & Files =====================
set "ROOT=%ProgramData%\UnsignedDriverInstall"
set "LOG=%ROOT%\install.log"
set "STAGE2=%ROOT%\Stage2.cmd"
if not exist "%ROOT%" mkdir "%ROOT%" >nul 2>&1

:: ===================== Create Stage 2 (runs at startup as SYSTEM) =====================
if defined DRY_RUN echo DEBUG: before Stage2 write
> "%STAGE2%" (
  echo @echo off
  echo setlocal EnableExtensions EnableDelayedExpansion
  echo set "INF=%INF%"
  echo set "SUBDIRS=%SUBDIRS%"
  echo echo ^>^> Installing driver: "%%INF%%"
  echo if "%%SUBDIRS%%"=="1" ^
   pnputil /add-driver "%%INF%%" /install /subdirs ^
  ^&^& echo pnputil completed ^
  ^|^| echo pnputil failed with errorlevel %%ERRORLEVEL%%
  echo if not "%%SUBDIRS%%"=="1" ^
   pnputil /add-driver "%%INF%%" /install ^
  ^&^& echo pnputil completed ^
  ^|^| echo pnputil failed with errorlevel %%ERRORLEVEL%%
  echo echo ^>^> Re-enabling driver signature enforcement...
  echo bcdedit /set nointegritychecks off
  echo bcdedit /set testsigning off
  echo echo ^>^> Cleaning up scheduled task...
  echo schtasks /Delete /TN "\InstallUnsignedDriverStage2" /F
  echo echo ^>^> Rebooting to apply enforcement...
  echo shutdown /r /t 5 /c "Driver installed. Re-enabling signature enforcement and rebooting."
  echo endlocal
)
if defined DRY_RUN echo DEBUG: after Stage2 write at "%STAGE2%"

if not exist "%STAGE2%" (
  echo Failed to write Stage 2 script at "%STAGE2%".
  echo.
  echo Press any key to exit...
  pause >nul
  goto :EOF
)

:: ===================== Register Scheduled Task =====================
echo.
if defined DRY_RUN echo DEBUG: before schtasks create
echo Creating startup task to install the driver after enforcement is disabled...
%RUN%schtasks /Create ^
  /TN "\InstallUnsignedDriverStage2" ^
  /SC ONSTART ^
  /RL HIGHEST ^
  /RU "SYSTEM" ^
  /TR "cmd.exe /c \"\"%STAGE2%\" ^>^> \"^%ProgramData^%\UnsignedDriverInstall\install.log\" 2^>^&1\"" ^
  /F
if defined DRY_RUN echo DEBUG: after schtasks create

if errorlevel 1 (
  echo Failed to create startup task.
  echo.
  echo Press any key to exit...
  pause >nul
  goto :EOF
)

echo Task created. Log: "%LOG%"
echo Driver INF: "%INF%"
if "%SUBDIRS%"=="1" (echo Including subdirectories.) else (echo Not including subdirectories.)

:: ===================== Detect Secure Boot =====================
if defined DRY_RUN echo DEBUG: before secure boot check
for /f "usebackq delims=" %%A in (`powershell -NoProfile -Command "try { if (Confirm-SecureBootUEFI) { 'ON' } else { 'OFF' } } catch { 'OFF' }"`) do set "SECUREBOOT=%%A"

echo Secure Boot: %SECUREBOOT%

:: ===================== Branch: Secure Boot OFF (automatic) =====================
if /I "%SECUREBOOT%"=="OFF" (
  echo.
  echo Disabling enforcement for the next boot...
  %RUN%bcdedit /set testsigning on
  if errorlevel 1 echo Warning: failed to set testsigning on.
  %RUN%bcdedit /set nointegritychecks on
  if errorlevel 1 echo Warning: failed to set nointegritychecks on.

  echo.
  echo The system will reboot in 5 seconds to install the driver automatically.
  %RUN%shutdown /r /t 5 /c "Temporarily disabling driver signature enforcement to install driver."
  goto :EOF
)

:: ===================== Branch: Secure Boot ON (manual step once) =====================
echo.
echo Secure Boot is ENABLED. Windows will ignore testsigning/nointegritychecks.
echo I will reboot you to Advanced Startup. On the blue screen, select:
echo   Troubleshoot -> Advanced options -> Startup Settings -> Restart
echo   Then press: 7  (Disable driver signature enforcement)
echo After Windows starts, the task will install the driver automatically and then reboot to re-enable enforcement.
echo.
echo Rebooting in 10 seconds to Advanced Startup...
timeout /t 10 >nul
%RUN%shutdown /r /o /t 5 /c "Choose: Disable driver signature enforcement (7). Windows will then auto-install the driver."
goto :EOF

:: ===================== Helper: Auto-Find INF =====================
:AutoFindINF
set "FOUND="
REM Try to find specific Bartels FTDI INFs first
for /f "delims=" %%F in ('dir /b /s /a:-d "%TEMP_DIR%\ftdibus*Bami.inf" 2^>nul') do (
  if not defined FOUND (
    set "INF=%%~fF"
    set "FOUND=1"
  )
)
if defined FOUND goto :AutoFindINF_end
for /f "delims=" %%F in ('dir /b /s /a:-d "%TEMP_DIR%\ftdiport*Bami.inf" 2^>nul') do (
  if not defined FOUND (
    set "INF=%%~fF"
    set "FOUND=1"
  )
)
if defined FOUND goto :AutoFindINF_end
REM Otherwise, take the first .inf anywhere
for /f "delims=" %%F in ('dir /b /s /a:-d "%TEMP_DIR%\*.inf" 2^>nul') do (
  if not defined FOUND (
    set "INF=%%~fF"
    set "FOUND=1"
  )
)
if defined FOUND goto :AutoFindINF_end
REM If no INF file, fallback to first top-level directory so /subdirs can install everything
for /f "delims=" %%D in ('dir /b /ad "%TEMP_DIR%" 2^>nul') do (
  if not defined FOUND (
    set "INF=%TEMP_DIR%\%%D"
    set "FOUND=1"
  )
)
:AutoFindINF_end
exit /b 0
