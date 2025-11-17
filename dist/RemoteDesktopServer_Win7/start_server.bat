@echo off
REM Remote Desktop Server for Windows 7
REM File-based communication with Python client

echo === Remote Desktop Server for Windows 7 ===
echo.

REM Get the directory where this batch file is located
set "SCRIPT_DIR=%~dp0"

REM Default to the network share where Python client writes commands
set "DEFAULT_FOLDER=\\BIPHUB\RemoteDesktopServer_Win7"

REM If no argument provided, use default folder
if "%~1"=="" (
    set "SHARED_FOLDER=%DEFAULT_FOLDER%"
) else (
    set "SHARED_FOLDER=%~1"
)

REM Create folder if it doesn't exist
if not exist "%SHARED_FOLDER%" (
    echo Creating folder: %SHARED_FOLDER%
    mkdir "%SHARED_FOLDER%" 2>nul
    if errorlevel 1 (
        echo ERROR: Could not create folder %SHARED_FOLDER%
        echo Please run as Administrator or choose a different folder
        pause
        exit /b 1
    )
)

echo Starting server...
echo Shared folder: %SHARED_FOLDER%
echo.
echo Server will monitor this folder for command.json files
echo Press Ctrl+C to exit
echo.

REM Change to shared folder and run server
cd /d "%SHARED_FOLDER%"
"%SCRIPT_DIR%RemoteDesktopServer.exe" "%SHARED_FOLDER%"

echo.
echo Server stopped.
pause
