@echo off
REM Build script for MicroscopeServer C# application
REM This compiles the C# project using MSBuild

echo Building MicroscopeServer...
echo.

REM Use MSBuild from .NET Framework 4.0
C:\Windows\Microsoft.NET\Framework\v4.0.30319\MSBuild.exe MicroscopeServer.csproj /p:Configuration=Release

if %ERRORLEVEL% EQU 0 (
    echo.
    echo Build succeeded! Executable located at:
    echo bin\Release\MicroscopeServer.exe
) else (
    echo.
    echo Build failed with error code %ERRORLEVEL%
)

pause
