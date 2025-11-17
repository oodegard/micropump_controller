@echo off
REM Create network share for micropump_controller repo
REM Must run as Administrator

echo Creating network share for micropump_controller...
echo.

REM Check if already shared
net share micropump_controller >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Share already exists. Removing old share...
    net share micropump_controller /delete /yes
)

REM Create new share with full access
net share micropump_controller=C:\git\micropump_controller /grant:everyone,FULL

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo SUCCESS: Share created!
    echo ========================================
    echo.
    echo Share name: micropump_controller
    echo Path: C:\git\micropump_controller
    echo Network path: \\%COMPUTERNAME%\micropump_controller
    echo.
    echo Test access with:
    echo   dir \\%COMPUTERNAME%\micropump_controller
    echo.
    echo Or from another computer:
    echo   dir \\BIPHUB\micropump_controller
    echo.
) else (
    echo.
    echo ERROR: Failed to create share
    echo Make sure you ran this as Administrator
    echo.
)

pause
