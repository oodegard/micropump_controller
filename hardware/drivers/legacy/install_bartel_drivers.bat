@echo off

:: BatchGotAdmin
:-------------------------------------
REM  --> Check for permissions
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

:: Set Variables
set ZIP_FILE=Bartels_controller_XU7_USB_Driver_2.08.30_cert.zip
set TEMP_DIR=%TEMP%\DriverInstall
set PS_SCRIPT=install_cert_and_drivers.ps1
set CERT_FILE=MicropumpTestSigning.cer

:: Create Temporary Directory
if exist "%TEMP_DIR%" rmdir /s /q "%TEMP_DIR%"
mkdir "%TEMP_DIR%"

:: Unzip Driver Folder
powershell -Command "Expand-Archive -Path \"%~dp0%ZIP_FILE%\" -DestinationPath \"%TEMP_DIR%\" -Force"

:: Install Certificate
powershell -Command "Import-Certificate -FilePath \"%TEMP_DIR%\%CERT_FILE%\" -CertStoreLocation Cert:\LocalMachine\Root"
powershell -Command "Import-Certificate -FilePath \"%TEMP_DIR%\%CERT_FILE%\" -CertStoreLocation Cert:\LocalMachine\TrustedPublisher"

:: Run PowerShell Script to Install Drivers
powershell -NoProfile -ExecutionPolicy Bypass -File "%TEMP_DIR%\%PS_SCRIPT%" -CertPath "%TEMP_DIR%\%CERT_FILE%"

:: Cleanup
rmdir /s /q "%TEMP_DIR%"

echo Installation complete. Press any key to exit.
pause