@echo off
REM Remote Desktop Server for Windows 7 - Microscope Control
REM Runs directly from the C# build output folder

echo === Remote Desktop Server for Windows 7 ===
echo.

REM Get the directory where this batch file is located (repo root)
set "REPO_ROOT=%~dp0"

REM Path to the built executable (runs from build output directly)
set "SERVER_EXE=%REPO_ROOT%remote_desktop_server_cs\bin\Release\RemoteDesktopServer.exe"

REM Default shared folder for file-based communication
REM Now using the entire repo share instead of separate RemoteDesktopServer_Win7 share
set "DEFAULT_FOLDER=\\BIPHUB\micropump_controller"

REM If no argument provided, use default folder
if "%~1"=="" (
    set "SHARED_FOLDER=%DEFAULT_FOLDER%"
) else (
    set "SHARED_FOLDER=%~1"
)

REM Check if executable exists
if not exist "%SERVER_EXE%" (
    echo ERROR: Server executable not found at:
    echo   %SERVER_EXE%
    echo.
    echo Please build the C# project first:
    echo   C:\Windows\Microsoft.NET\Framework\v4.0.30319\MSBuild.exe remote_desktop_server_cs\RemoteDesktopServer.csproj /p:Configuration=Release
    echo.
    pause
    exit /b 1
)

REM Create shared folder if it doesn't exist
if not exist "%SHARED_FOLDER%" (
    echo Creating shared folder: %SHARED_FOLDER%
    mkdir "%SHARED_FOLDER%" 2>nul
    if errorlevel 1 (
        echo ERROR: Could not create folder %SHARED_FOLDER%
        echo Please run as Administrator or choose a different folder
        pause
        exit /b 1
    )
)

echo Starting server...
echo Executable: %SERVER_EXE%
echo Shared folder: %SHARED_FOLDER%
echo.
echo Server will monitor %SHARED_FOLDER%\status\ for command.json files
echo Press Ctrl+C to exit
echo.

REM Run server with shared folder as argument
"%SERVER_EXE%" "%SHARED_FOLDER%"

echo.
echo Server stopped.
pause
