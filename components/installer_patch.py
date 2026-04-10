import re
from typing import Final

import requests

ULTIMATE_INSTALLER_URL: Final[str] = (
    "https://raw.githubusercontent.com/FR33THYFR33THY/Ultimate/main/"
    "4%20Installers/1%20Installers.ps1"
)


def fetch_ultimate_installer(timeout: int = 30) -> str:
    response = requests.get(ULTIMATE_INSTALLER_URL, timeout=timeout)
    response.raise_for_status()
    return response.text


def patch_installer_script(script_text: str) -> str:
    """Patch Ultimate installer with local custom additions only if missing."""
    patched = script_text

    if "Microsoft Office 2024 LTSC Edition" in patched and "function show-miscellaneous-menu" in patched:
        return patched

    patched = patched.replace(
        'Write-Host "24. Valorant`n"',
        'Write-Host "24. Valorant"\n'
        '        Write-Host "25. Microsoft Office 2024 LTSC Edition"\n'
        '        Write-Host "26. Miscellaneous`n"',
    )

    patched = patched.replace(
        "$choice -match '^(2[0-4]|1[0-9]|[1-9])$'",
        "$choice -match '^(2[0-6]|1[0-9]|[1-9])$'",
    )

    misc_menu_function = """
function show-miscellaneous-menu {
    Clear-Host
    Write-Host "Choose a tool:" -ForegroundColor Green
    Write-Host ""
    Write-Host "1. Exit" -ForegroundColor Red
    Write-Host "2. MAS(Activate windows,etc)" -ForegroundColor Cyan

    $launcherChoice = Read-Host " "
    if ($launcherChoice -match '^[1-2]$') {
        switch ($launcherChoice) {
            1 {
                Clear-Host
                show-menu
            }
            2 {
                Clear-Host
                Write-Host "Intializing MAS. . ."
                try {
                    $powershellCommand = "Set-ExecutionPolicy Bypass -Scope Process -Force; irm https://get.activated.win | iex"
                    Start-Process -FilePath "powershell.exe" -ArgumentList "-Command $powershellCommand" -Wait -PassThru -NoNewWindow | Out-Null
                }
                catch {
                    Write-Host "Unexpected error during Windows Activated: $($_.Exception.Message)"
                }
                show-miscellaneous-menu
            }
        }
    }
    else {
        Write-Host "Invalid input. Please select a valid option (1 - 2)."
    }
}
"""

    if "function show-miscellaneous-menu" not in patched:
        patched = re.sub(
            r"(show-menu\s*\r?\n\s*while \(\$true\) \{)",
            misc_menu_function + "\n\\1",
            patched,
            count=1,
            flags=re.MULTILINE,
        )

    office_case = """
       25 {

Clear-Host

Write-Host "Installing: Microsoft Office 2024 LTSC Edition..."
$toolPath = "$env:TEMP\\officedeploymenttool_18227-20162.exe"
$configurationPath = "$env:TEMP\\OfficeDeployment\\configuration-Office365-x64.xml"

IWR "https://download.microsoft.com/download/2/7/A/27AF1BE6-DD20-4CB4-B154-EBAB8A7D4A7E/officedeploymenttool_18227-20162.exe" -OutFile $toolPath
Start-Process -FilePath $toolPath -ArgumentList "/quiet /extract:$env:TEMP\\OfficeDeployment" -Wait

$configureOffice = @"
<Configuration ID="7ccad42d-bf21-44c0-8399-a0d9fba9ba0c">
  <Add OfficeClientEdition="64" Channel="PerpetualVL2024">
    <Product ID="ProPlus2024Volume" PIDKEY="XJ2XN-FW8RK-P4HMP-DKDBV-GCVGB">
      <Language ID="en-gb" />
      <ExcludeApp ID="Lync" />
      <ExcludeApp ID="OneDrive" />
      <ExcludeApp ID="Outlook" />
    </Product>
  </Add>
  <Property Name="SharedComputerLicensing" Value="0" />
  <Property Name="FORCEAPPSHUTDOWN" Value="FALSE" />
  <Property Name="DeviceBasedLicensing" Value="0" />
  <Property Name="SCLCacheOverride" Value="0" />
  <Property Name="AUTOACTIVATE" Value="1" />
  <Updates Enabled="TRUE" />
</Configuration>
"@

$configureOffice | Set-Content -Path $configurationPath -Force
Start-Process -FilePath "$env:TEMP\\OfficeDeployment\\setup.exe" -ArgumentList "/configure $configurationPath" -Wait

show-menu

          }
       26 {

Clear-Host

show-miscellaneous-menu

          }
"""

    if "25 {" not in patched and "Microsoft Office 2024 LTSC Edition" in patched:
        patched = patched.replace(
            "       24 {",
            office_case + "\n       24 {",
            1,
        )

    patched = patched.replace(
        "Invalid input. Please select a valid option (1-24).",
        "Invalid input. Please select a valid option (1-26).",
    )

    return patched
