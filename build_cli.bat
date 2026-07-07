@echo off
echo Building ZTalon CLI with enhanced compatibility...

:: Check for required dependencies
python -c "import requests, nuitka, certifi" 2>nul
if errorlevel 1 (
    echo ERROR: Missing required dependencies. Run: pip install -r requirements.txt
    pause
    exit /b 1
)

echo Checking Nuitka version...
python -c "import nuitka; print(f'Nuitka version: {nuitka.__version__}')"

if exist dist\cli rmdir /s /q dist\cli
if exist build\cli rmdir /s /q build\cli

echo Starting Nuitka compilation for CLI...
nuitka --onefile --standalone --remove-output ^
    --msvc=latest ^
    --windows-icon-from-ico=ICON.ico ^
    --show-progress --show-memory ^
    --windows-console-mode=force ^
    --enable-plugin=anti-bloat ^
    --assume-yes-for-downloads ^
    --output-filename=ZTalon-CLI.exe ^
    --windows-uac-admin ^
    --output-dir=dist\cli ^
    --follow-imports ^
    --include-data-files="ChakraPetch-Regular.ttf=ChakraPetch-Regular.ttf" ^
    --include-data-files="components/app_install.py=components/app_install.py" ^
    --include-data-files="components/debloat_windows.py=components/debloat_windows.py" ^
    --include-data-files="components/__init__.py=components/__init__.py" ^
    --include-data-files="components/utils.py=components/utils.py" ^
    --enable-plugin=tk-inter ^
    --windows-company-name="sogik Development" ^
    --windows-product-name="ZTalon Windows Optimizer CLI" ^
    --windows-file-version="1.0.1.0" ^
    --windows-product-version="1.0.1" ^
    --windows-file-description="ZTalon CLI - Windows Optimization Tool (Terminal Mode)" ^
    --copyright="Copyright (c) 2025 sogik. Licensed under BSD-3-Clause." ^
    --python-flag=no_warnings ^
    init.py

if not exist "dist\cli\ZTalon-CLI.exe" (
    echo ERROR: Build failed! ZTalon-CLI.exe not found.
    if not defined GITHUB_ACTIONS pause
    exit /b 1
)

echo.
echo Build completed! Creating checksums...

:: Create checksums for verification
cd dist\cli
certutil -hashfile ZTalon-CLI.exe SHA256 > ZTalon-CLI.exe.sha256
certutil -hashfile ZTalon-CLI.exe MD5 > ZTalon-CLI.exe.md5

echo.
echo Checksums created:
type ZTalon-CLI.exe.sha256
echo.

cd ..\..
echo ✅ CLI Build completed successfully!
if not defined GITHUB_ACTIONS pause
