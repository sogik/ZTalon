@echo off
echo Building ZTalon GUI with enhanced compatibility...

:: Check for required dependencies
python -c "import requests, nuitka, certifi, PyQt5" 2>nul
if errorlevel 1 (
    echo ERROR: Missing required dependencies. Run: pip install -r requirements.txt
    pause
    exit /b 1
)

echo Checking Nuitka version...
python -c "import nuitka; print(f'Nuitka version: {nuitka.__version__}')"

if exist dist\gui rmdir /s /q dist\gui
if exist build\gui rmdir /s /q build\gui

echo Starting Nuitka compilation for GUI...
nuitka --onefile --standalone --remove-output ^
    --windows-icon-from-ico=ICON.ico ^
    --show-progress --show-memory ^
    --windows-console-mode=disable ^
    --enable-plugin=anti-bloat ^
    --enable-plugin=pyqt5 ^
    --assume-yes-for-downloads ^
    --output-filename=ZTalon.exe ^
    --windows-uac-admin ^
    --output-dir=dist\gui ^
    --follow-imports ^
    --include-data-files="ChakraPetch-Regular.ttf=ChakraPetch-Regular.ttf" ^
    --include-data-files="components/app_install.py=components/app_install.py" ^
    --include-data-files="components/debloat_windows.py=components/debloat_windows.py" ^
    --include-data-files="components/__init__.py=components/__init__.py" ^
    --include-data-files="components/utils.py=components/utils.py" ^
    --include-package=gui ^
    --windows-company-name="sogik Development" ^
    --windows-product-name="ZTalon Windows Optimizer GUI" ^
    --windows-file-version="1.0.1.0" ^
    --windows-product-version="1.0.1" ^
    --windows-file-description="ZTalon GUI - Windows Optimization Tool (Graphical Mode)" ^
    --copyright="Copyright (c) 2025 sogik. Licensed under BSD-3-Clause." ^
    --python-flag=no_warnings ^
    gui\main_gui.py

if not exist "dist\gui\ZTalon.exe" (
    echo ERROR: Build failed! ZTalon.exe not found.
    pause
    exit /b 1
)

echo.
echo Build completed! Creating checksums...

:: Create checksums for verification
cd dist\gui
certutil -hashfile ZTalon.exe SHA256 > ZTalon.exe.sha256
certutil -hashfile ZTalon.exe MD5 > ZTalon.exe.md5

echo.
echo Checksums created:
type ZTalon.exe.sha256
echo.

cd ..\..
echo ✅ GUI Build completed successfully!
pause
