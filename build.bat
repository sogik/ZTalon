@echo off
nuitka --onefile --standalone --enable-plugin=pyqt5 --remove-output --windows-icon-from-ico=ICON.ico --windows-console-mode=disable --windows-uac-admin --output-dir=dist --include-data-files="ChakraPetch-Regular.ttf=ChakraPetch-Regular.ttf" --include-data-files="browser_selection.png=browser_selection.png" --include-data-files="additional_software_offer.png=additional_software_offer.png" init.py
pause
