@echo off
echo Building ZTalon with enhanced compatibility...

:: Check for required dependencies
python -c "import requests, nuitka" 2>nul
if errorlevel 1 (
    echo ERROR: Missing required dependencies. Run: pip install -r requirements.txt
    pause
    exit /b 1
)

if exist dist rmdir /s /q dist
if exist build rmdir /s /q build

nuitka --onefile --standalone --remove-output ^
    --windows-icon-from-ico=ICON.ico ^
    --show-progress --show-memory ^
    --windows-console-mode=force ^
    --enable-plugin=anti-bloat ^
    --assume-yes-for-downloads ^
    --output-filename=ZTalon.exe ^
    --windows-uac-admin ^
    --output-dir=dist ^
    --follow-imports ^
    --include-data-files="ChakraPetch-Regular.ttf=ChakraPetch-Regular.ttf" ^
    --include-data-files="components/app_install.py=components/app_install.py" ^
    --include-data-files="components/debloat_windows.py=components/debloat_windows.py" ^
    --include-data-files="components/__init__.py=components/__init__.py" ^
    --include-data-files="components/utils.py=components/utils.py" ^
    --enable-plugin=tk-inter ^
    --windows-company-name="sogik Development" ^
    --windows-product-name="ZTalon Windows Optimizer" ^
    --windows-file-version="1.0.1.0" ^
    --windows-product-version="1.0.1" ^
    --windows-file-description="Enhanced Open Source Windows Optimization and Debloating Tool with SSL Support" ^
    --copyright="Copyright (c) 2025 sogik. Licensed under BSD-3-Clause." ^
    --windows-original-filename="ZTalon.exe" ^
    --windows-internal-name="ZTalon" ^
    --python-flag=no_warnings ^
    init.py

if not exist "dist\ZTalon.exe" (
    echo ERROR: Build failed! ZTalon.exe not found.
    pause
    exit /b 1
)

echo.
echo Build completed! Creating checksums...

:: Create checksums for verification
cd dist
certutil -hashfile ZTalon.exe SHA256 > ZTalon.exe.sha256
certutil -hashfile ZTalon.exe MD5 > ZTalon.exe.md5

echo.
echo Checksums created:
type ZTalon.exe.sha256
echo.

cd ..
echo ✅ Build completed successfully!
pause