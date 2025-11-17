@echo off
echo ========================================
echo Remote Desktop Server for Windows 7
echo ========================================
echo.

REM Use Python from the shared Anaconda installation
set PYTHON_PATH=\\BIPHUB\anaconda\python.exe
set PYTHONPATH=\\BIPHUB\micropump;\\BIPHUB\micropump\.venv\Lib\site-packages

REM Check if we can access the shared Python
%PYTHON_PATH% --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Cannot access shared Python!
    echo Expected at: %PYTHON_PATH%
    echo.
    echo Make sure:
    echo   1. Ethernet cable is connected
    echo   2. You can access \\BIPHUB\anaconda
    pause
    exit /b 1
)

echo Found Python at: %PYTHON_PATH%
%PYTHON_PATH% --version
echo.
echo Starting server...
echo.

REM Run the server using shared Python and packages
%PYTHON_PATH% remote_desktop_server_win7.py

pause
