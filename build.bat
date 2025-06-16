@echo off
nuitka --onefile --standalone --remove-output --windows-icon-from-ico=ICON.ico --windows-console-mode=disable --windows-uac-admin --output-dir=dist --follow-imports --include-data-files="ChakraPetch-Regular.ttf=ChakraPetch-Regular.ttf" --include-data-files="app_install.py=app_install.py" --include-data-files="debloat_windows.py=debloat_windows.py" init.py
pause