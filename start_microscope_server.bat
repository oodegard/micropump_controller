@echo off
REM Microscope Control Server for Windows 7
REM Runs directly from the C# build output folder

echo === Microscope Control Server for Windows 7 ===
echo.

REM Get the directory where this batch file is located (repo root)
set "REPO_ROOT=%~dp0"

REM Path to the built executable (runs from build output directly)
set "SERVER_EXE=%REPO_ROOT%microscope_server\bin\Release\MicroscopeServer.exe"

REM Default shared folder for file-based communication
REM Using the entire repo share
set "DEFAULT_FOLDER=\\BIPHUB\micropump_controller"

set "SHARED_FOLDER=%DEFAULT_FOLDER%"
set "SHARED_FOLDER_SET=0"
set "SCREEN_OPTION="

:parse_args
if "%~1"=="" goto args_done

if /I "%~1"=="--screen" (
    if "%~2"=="" (
        echo ERROR: --screen requires an index value.
        exit /b 1
    )
    set "SCREEN_OPTION=--screen %~2"
    shift
    shift
    goto parse_args
)

if "%SHARED_FOLDER_SET%"=="0" (
    set "SHARED_FOLDER=%~1"
    set "SHARED_FOLDER_SET=1"
    shift
    goto parse_args
)

echo ERROR: Unrecognized argument %1
exit /b 1

:args_done

REM Check if executable exists
if not exist "%SERVER_EXE%" (
    echo ERROR: Server executable not found at:
    echo   %SERVER_EXE%
    echo.
    echo Please build the C# project first:
    echo   C:\Windows\Microsoft.NET\Framework\v4.0.30319\MSBuild.exe microscope_server\MicroscopeServer.csproj /p:Configuration=Release
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
if defined SCREEN_OPTION (
    for /f "tokens=2" %%s in ("%SCREEN_OPTION%") do (
        echo Screen index: %%s
    )
) else (
    echo Screen index: primary (default)
)
echo.
echo Server will monitor %SHARED_FOLDER%\status\ for command.json files
echo Press Ctrl+C to exit
echo.

REM Run server with shared folder and optional screen argument
if defined SCREEN_OPTION (
    "%SERVER_EXE%" "%SHARED_FOLDER%" %SCREEN_OPTION%
) else (
    "%SERVER_EXE%" "%SHARED_FOLDER%"
)

echo.
echo Server stopped.
pause
