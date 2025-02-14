@echo off
nuitka --onefile --standalone --remove-output --windows-icon-from-ico=ICON.ico --windows-console-mode=disable --windows-uac-admin --output-dir=dist --follow-imports --include-data-files="ChakraPetch-Regular.ttf=ChakraPetch-Regular.ttf" init.py
pause