@echo off
echo ========================================
echo   Building ZTalon - CLI and GUI
echo ========================================
echo.

echo [1/2] Building CLI version...
call build_cli.bat
if errorlevel 1 (
    echo ERROR: CLI build failed!
    pause
    exit /b 1
)

echo.
echo [2/2] Building GUI version...
call build_gui.bat
if errorlevel 1 (
    echo ERROR: GUI build failed!
    pause
    exit /b 1
)

echo.
echo ========================================
echo   Both builds completed successfully!
echo ========================================
echo.
echo CLI: dist\cli\ZTalon-CLI.exe
echo GUI: dist\gui\ZTalon.exe
echo.
pause
