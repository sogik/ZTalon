@echo off
echo Delegating to build_cli.bat...

if not exist "build_cli.bat" (
    echo ERROR: build_cli.bat not found.
    pause
    exit /b 1
)

call build_cli.bat
exit /b %errorlevel%
