@echo off
echo Building ZTalon...
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
    --enable-plugin=tk-inter ^
    --windows-company-name="sogik" ^
    --windows-product-name="ZTalon" ^
    --windows-file-version="1.0.0" ^
    --windows-product-version="1.0.0" ^
    --windows-file-description="Open Source Windows Optimization and Debloating Tool" ^
    --copyright="Copyright (c) 2025 sogik. Licensed under BSD-3-Clause." ^
    --trademarks="ZTalon is a trademark of sogik" ^
    --windows-original-filename="ZTalon.exe" ^
    --windows-internal-name="ZTalon" ^
    init.py

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
type ZTalon.exe.md5

cd ..
pause