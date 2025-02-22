function Get-FileFromWeb {
    param ([Parameter(Mandatory)][string]$URL, [Parameter(Mandatory)][string]$File)
    function Show-Progress {
        param ([Parameter(Mandatory)][Single]$TotalValue, [Parameter(Mandatory)][Single]$CurrentValue, [Parameter(Mandatory)][string]$ProgressText, [Parameter()][int]$BarSize = 10, [Parameter()][switch]$Complete)
        $percent = $CurrentValue / $TotalValue
        $percentComplete = $percent * 100
        if ($psISE) { Write-Progress "$ProgressText" -id 0 -percentComplete $percentComplete }
        else { Write-Host -NoNewLine "`r$ProgressText $(''.PadRight($BarSize * $percent, [char]9608).PadRight($BarSize, [char]9617)) $($percentComplete.ToString('##0.00').PadLeft(6)) % " }
    }
    try {
        $request = [System.Net.HttpWebRequest]::Create($URL)
        $response = $request.GetResponse()
        if ($response.StatusCode -eq 401 -or $response.StatusCode -eq 403 -or $response.StatusCode -eq 404) { throw "Remote file either doesn't exist, is unauthorized, or is forbidden for '$URL'." }
        if ($File -match '^\.\\') { $File = Join-Path (Get-Location -PSProvider 'FileSystem') ($File -Split '^\.')[1] }
        if ($File -and !(Split-Path $File)) { $File = Join-Path (Get-Location -PSProvider 'FileSystem') $File }
        if ($File) { $fileDirectory = $([System.IO.Path]::GetDirectoryName($File)); if (!(Test-Path($fileDirectory))) { [System.IO.Directory]::CreateDirectory($fileDirectory) | Out-Null } }
        [long]$fullSize = $response.ContentLength
        [byte[]]$buffer = new-object byte[] 1048576
        [long]$total = [long]$count = 0
        $reader = $response.GetResponseStream()
        $writer = new-object System.IO.FileStream $File, 'Create'
        do {
            $count = $reader.Read($buffer, 0, $buffer.Length)
            $writer.Write($buffer, 0, $count)
            $total += $count
            if ($fullSize -gt 0) { Show-Progress -TotalValue $fullSize -CurrentValue $total -ProgressText " $($File.Name)" }
        } while ($count -gt 0)
    }
    finally {
        $reader.Close()
        $writer.Close()
    }
}
function show-menu {
    Clear-Host
    Write-Host "Game launchers, programs and web browsers:" -ForegroundColor Green
    Write-Host "-Disable hardware acceleration" -ForegroundColor Green
    Write-Host "-Turn off running at startup" -ForegroundColor Green
    Write-Host "-Deactivate overlays" -ForegroundColor Green
    Write-Host ""
    Write-Host "Lower GPU usage and higher framerates reduce latency." -ForegroundColor Green
    Write-Host "Optimize your game settings to achieve this." -ForegroundColor Green
    Write-Host "Further tuning can be done via config files or launch options." -ForegroundColor Green
    Write-Host ""
    Write-Host "1. Exit" -ForegroundColor Red
    Write-Host "2. 7-Zip" -ForegroundColor Cyan
    Write-Host "3. Game Launchers" -ForegroundColor Cyan
    Write-Host "4. Discord" -ForegroundColor Cyan
    Write-Host "5. Spotify" -ForegroundColor Cyan
    Write-Host "6. Escape From Tarkov" -ForegroundColor Cyan
    Write-Host "7. Browsers" -ForegroundColor Cyan
    Write-Host "8. League Of Legends" -ForegroundColor Cyan
    Write-Host "9. Notepad ++" -ForegroundColor Cyan
    Write-Host "10. OBS Studio" -ForegroundColor Cyan
    Write-Host "11. Roblox" -ForegroundColor Cyan
    Write-Host "12. Valorant" -ForegroundColor Cyan
    Write-Host "13. Microsoft Office 2024 LSTC Edition" -ForegroundColor Cyan
    Write-Host "14. Miscellaneous" -ForegroundColor Cyan
}


function show-browser-menu {
    Clear-Host
    Write-Host "Choose a browser to install:" -ForegroundColor Green
    Write-Host ""
    Write-Host "1. Exit" -ForegroundColor Red
    Write-Host "2. Google Chrome" -ForegroundColor Cyan
    Write-Host "3. Firefox" -ForegroundColor Cyan
    Write-Host "4. Thorium Browser" -ForegroundColor Cyan
    Write-Host "5. Brave Browser" -ForegroundColor Cyan

    $browserChoice = Read-Host " "
    $firefoxExtensions = @(
        "https://addons.mozilla.org/en-US/firefox/addon/decentraleyes/",
        "https://addons.mozilla.org/en-US/firefox/addon/ublock-origin/",
        "https://addons.mozilla.org/en-US/firefox/addon/privacy-badger17/",
        "https://addons.mozilla.org/en-US/firefox/addon/react-devtools/",
        "https://addons.mozilla.org/en-US/firefox/addon/search_by_image/"
    )
    $chromiumExtensions = @(
        "https://chromewebstore.google.com/detail/ublock-origin/cjpalhdlnbpafiamejdnhcphjbkeiagm",
        "https://chromewebstore.google.com/detail/privacy-badger/pkehgijcmpdhfbdbbnkijodmdjhbjlgp",
        "https://chromewebstore.google.com/detail/react-developer-tools/fmkadmapgofadopljbjfkapdkoienihi",
        "https://chromewebstore.google.com/detail/search-by-image/cnojnbdhbhnkbcieeekonklommdnndci",
        "https://chromewebstore.google.com/detail/decentraleyes/ldpochfccmkkmhdbclfhpagapcfdljkj"
    )

    $thoriumPaths = @(
        "$env:LOCALAPPDATA\Thorium\Application\thorium.exe"
    )

    $chromePaths = @(
        "C:\Program Files\Google\Chrome\Application\chrome.exe",
        "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"

    )

    $firefoxPaths = @(
        "C:\Program Files\Mozilla Firefox\firefox.exe",
        "C:\Program Files (x86)\Mozilla Firefox\firefox.exe"
    )

    $bravePaths = @(
        "$env:LOCALAPPDATA\BraveSoftware\Brave-Browser\Application\brave.exe",
        "C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
    )
    if ($browserChoice -match '^[1-5]$') {
        switch ($browserChoice) {
            1 {
                Clear-Host
                show-menu
            }
            2 {
                Clear-Host
                Write-Host "Installing: Google Chrome . . ."
                # download google chrome
                Get-FileFromWeb -URL "https://dl.google.com/dl/chrome/install/googlechromestandaloneenterprise64.msi" -File "$env:TEMP\Chrome.msi"
                # install google chrome
                Start-Process -wait "$env:TEMP\Chrome.msi" -ArgumentList "/quiet"
                $chromePath = $chromePaths | Where-Object { Test-Path $_ } | Select-Object -First 1
                if ($chromePath) {
                    foreach ($extension in $chromiumExtensions) {
                        Start-Process $chromePath $extension
                    }
                }
                show-menu
            }
            3 {
                Clear-Host
                Write-Host "Installing: Firefox . . ."
                # download firefox
                Get-FileFromWeb -URL "https://download.mozilla.org/?product=firefox-latest-ssl&os=win&lang=en-US" -File "$env:TEMP\Firefox Installer.exe"
                # install firefox
                Start-Process -wait "$env:TEMP\Firefox Installer.exe" -ArgumentList "/S"

                $firefoxPath = $firefoxPaths | Where-Object { Test-Path $_ } | Select-Object -First 1
                if ($firefoxPath) {
                    foreach ($extension in $firefoxExtensions) {
                        Start-Process $firefoxPath $extension
                    }
                }

                show-menu
            }
            4 {
                Clear-Host
                Write-Host "Installing: Thorium Browser . . ."
                # download thorium browser
                Get-FileFromWeb -URL "https://github.com/Alex313031/Thorium-Win/releases/download/M130.0.6723.174/thorium_AVX2_mini_installer.exe" -File "$env:TEMP\Thorium Browser.exe"
                # install thorium browser
                Start-Process -wait "$env:TEMP\Thorium Browser.exe" -ArgumentList "/S"
                $thoriumPath = $thoriumPaths | Where-Object { Test-Path $_ } | Select-Object -First 1
                if ($thoriumPath) {
                    foreach ($extension in $chromiumExtensions) {
                        Start-Process $thoriumPath $extension
                    }
                }
                show-menu
            }
            5 {
                Clear-Host
                Write-Host "Installing: Brave Browser . . ."
                # download brave browser
                Get-FileFromWeb -URL "https://laptop-updates.brave.com/latest/winx64" -File "$env:TEMP\BraveBrowserSetup.exe"
                # install brave browser
                Start-Process -wait "$env:TEMP\BraveBrowserSetup.exe" -ArgumentList "/silent", "/install"
                $bravePath = $bravePaths | Where-Object { Test-Path $_ } | Select-Object -First 1
                if ($bravePath) {
                    foreach ($extension in $chromiumExtensions) {
                        Start-Process $bravePath $extension
                    }
                }
                show-menu
            }
        }
    }
    else {
        Write-Host "Invalid input. Please select a valid option (1 - 5)."
    }

}

function show-launchers-menu {
    Clear-Host
    Write-Host "Choose a game launcher to install:" -ForegroundColor Green
    Write-Host ""
    Write-Host "1. Exit" -ForegroundColor Red
    Write-Host "2. Battle.net" -ForegroundColor Cyan
    Write-Host "3. Steam" -ForegroundColor Cyan
    Write-Host "4. Epic Games" -ForegroundColor Cyan
    Write-Host "5. Ubisoft Connect" -ForegroundColor Cyan
    Write-Host "6. Electronic Arts" -ForegroundColor Cyan
    Write-Host "7. Rockstar Games" -ForegroundColor Cyan
    Write-Host "8. GOG launcher" -ForegroundColor Cyan
    Write-Host "9. Plutonium" -ForegroundColor Cyan
    Write-Host "10.Origin" -ForegroundColor Cyan
    Write-Host "11.Faceit Launcher" -ForegroundColor Cyan

    $launcherChoice = Read-Host " "
    if ($launcherChoice -match '^[1-9]$|^11$' ) {
        switch ($launcherChoice ) {
            1 {
                Clear-Host
                show-menu
            }
            2 {
                Clear-Host
                Write-Host "Installing: Battle.net . . ."
                # download battle.net
                Get-FileFromWeb -URL "https://downloader.battle.net/download/getInstaller?os=win&installer=Battle.net-Setup.exe" -File "$env:TEMP\Battle.net.exe"
                # install battle.net
                Start-Process "$env:TEMP\Battle.net.exe" -ArgumentList '--lang=enUS --installpath="C:\Program Files (x86)\Battle.net"'
                # create battle.net shortcut
                $WshShell = New-Object -comObject WScript.Shell
                $Shortcut = $WshShell.CreateShortcut("$Home\Desktop\Battle.net.lnk")
                $Shortcut.TargetPath = "$env:SystemDrive\Program Files (x86)\Battle.net\Battle.net Launcher.exe"
                $Shortcut.Save()
                show-launchers-menu
            }
            3 {
                Clear-Host
                Write-Host "Installing: Steam . . ."
                # download steam
                Get-FileFromWeb -URL "https://cdn.cloudflare.steamstatic.com/client/installer/SteamSetup.exe" -File "$env:TEMP\Steam.exe"
                # install steam
                Start-Process -wait "$env:TEMP\Steam.exe" -ArgumentList "/S"
                show-launchers-menu
            }
            4 {
                Clear-Host
                Write-Host "Installing: Epic Games . . ."
                # download epic games
                Get-FileFromWeb -URL "https://epicgames-download1.akamaized.net/Builds/UnrealEngineLauncher/Installers/Win32/EpicInstaller-15.17.1.msi?launcherfilename=EpicInstaller-15.17.1.msi" -File "$env:TEMP\Epic Games.msi"
                # install epic games
                Start-Process -wait "$env:TEMP\Epic Games.msi" -ArgumentList "/quiet"
                show-launchers-menu
            }
            5 {
                Clear-Host
                Write-Host "Installing: Ubisoft Connect . . ."
                # download ubisoft connect
                Get-FileFromWeb -URL "https://static3.cdn.ubi.com/orbit/launcher_installer/UbisoftConnectInstaller.exe" -File "$env:TEMP\Ubisoft Connect.exe"
                # install ubisoft connect
                Start-Process -wait "$env:TEMP\Ubisoft Connect.exe" -ArgumentList "/S"
                show-launchers-menu
            }
            6 {
                Clear-Host
                Write-Host "Installing: Electronic Arts . . ."
                # download electronic arts
                Get-FileFromWeb -URL "https://origin-a.akamaihd.net/EA-Desktop-Client-Download/installer-releases/EAappInstaller.exe" -File "$env:TEMP\Electronic Arts.exe"
                # install electronic arts
                Start-Process "$env:TEMP\Electronic Arts.exe"
                show-launchers-menu
            }
            7 {
                Clear-Host
                Write-Host "Installing: Rockstar Games . . ."
                # download rockstar games
                Get-FileFromWeb -URL "https://gamedownloads.rockstargames.com/public/installer/Rockstar-Games-Launcher.exe" -File "$env:TEMP\Rockstar Games.exe"
                # install rockstar games
                Start-Process "$env:TEMP\Rockstar Games.exe"
                show-launchers-menu
            }
            8 {
                Clear-Host
                Write-Host "Installing: GOG launcher . . ."
                # download gog launcher
                Get-FileFromWeb -URL "https://webinstallers.gog-statics.com/download/GOG_Galaxy_2.0.exe" -File "$env:TEMP\GOG launcher.exe"
                # install gog launcher
                Start-Process "$env:TEMP\GOG launcher.exe"
                show-launchers-menu
            }
            9 {
                Clear-Host
                Write-Host "Installing: Plutonium . . ."
                # download plutonium
                Get-FileFromWeb -URL "https://cdn.plutonium.pw/updater/plutonium.exe" -File "$env:TEMP\Plutonium.exe"
                # create Plutonium folder in Program Files
                $plutoniumFolderPath = "$env:SystemDrive\Program Files (x86)\Plutonium"
                if (-Not (Test-Path -Path $plutoniumFolderPath)) {
                    New-Item -ItemType Directory -Path $plutoniumFolderPath
                }
                # move plutonium.exe to the Plutonium folder
                Move-Item -Path "$env:TEMP\Plutonium.exe" -Destination "$plutoniumFolderPath\Plutonium.exe"
                # create plutonium shortcut
                $WshShell = New-Object -comObject WScript.Shell
                $Shortcut = $WshShell.CreateShortcut("$Home\Desktop\Plutonium.lnk")
                $Shortcut.TargetPath = "$plutoniumFolderPath\Plutonium.exe"
                $Shortcut.Save()
                Start-Process "$plutoniumFolderPath\Plutonium.exe"
                show-launchers-menu
            }
            10 {
                Clear-Host
                Write-Host "Installing: Origin . . ."
                $localConfigurationPath = "$env:ProgramData\Origin\local.xml"
                # download origin
                Get-FileFromWeb -URL "https://download.dm.origin.com/origin/live/OriginSetup.exe" -File "$env:TEMP\OriginSetup.exe"
                # install origin
                Start-Process -wait "$env:TEMP\OriginSetup.exe" -ArgumentList "/S"


                # set the local.xml configuration file to read-only
                Set-ItemProperty -Path "$localConfigurationPath" -Name IsReadOnly -Value $true

                Clear-Host
                Write-Host "Installing Fuck off EA App . . . (Check Pretend EA App is Installed)"
                # download Fuck off EA App Installer
                Get-FileFromWeb -URL "https://github.com/p0358/Fuck_off_EA_App/releases/download/v6/Fuck_off_EA_App_installer.exe" -File "$env:TEMP\Fuck_off_EA_App_installer.exe"
                # install Fuck off EA App Installer
                Start-Process -wait "$env:TEMP\Fuck_off_EA_App_installer.exe"

                Clear-Host
                Write-Host "Installing: Punkbuster Service Updater . . . (Add Games to Punkbuster)"
                # download punkbuster service updater
                Get-FileFromWeb -URL "https://www.evenbalance.com/downloads/W/gui/pbsetup.zip" -File "$env:TEMP\pbsetup.zip"
                # extract punkbuster service updater
                Expand-Archive "$env:TEMP\pbsetup.zip" -DestinationPath "$env:TEMP\pbsetup" -ErrorAction SilentlyContinue
                # install punkbuster service updater
                Start-Process -wait "$env:TEMP\pbsetup\pbsetup.exe"


                show-launchers-menu


            }
            11 {
                Clear-Host
                Write-Host "Installing FaceIt Launcher . . ."
                #download faceit launcher
                Get-FileFromWeb -URL "https://faceit-client.faceit-cdn.net/release/FACEIT-setup-latest.exe" -File "$env:TEMP\FACEIT-setup-latest.exe"
                #install faceit launcher
                Start-Process -wait "$env:TEMP\FACEIT-setup-latest.exe" -ArgumentList "/S"
                Clear-Host

                Write-Host "Installing FaceIt Anti-Cheat . . ."
                #download face it AC
                Get-FileFromWeb -URL "https://anticheat-client.faceit-cdn.net/FACEITInstaller_64.exe" -File "$env:TEMP\FACEITInstaller_64.exe"
                #install face it AC
                Start-Process -wait "$env:TEMP\FACEITInstaller_64.exe" -ArgumentList "/S"

                show-launchers-menu

            }
        }
    }
    else {
        Write-Host "Invalid input. Please select a valid option (1 - 11)."
    }


}
function show-miscellaneous-menu {
    Clear-Host
    Write-Host "Choose a tool:" -ForegroundColor Green
    Write-Host ""
    Write-Host "1. Exit" -ForegroundColor Red
    Write-Host "2. MAS(Activate windows,etc)" -ForegroundColor Cyan

    $launcherChoice = Read-Host " "
    if ($launcherChoice -match '^[1-2]$|^11$' ) {
        switch ($launcherChoice ) {
            1 {
                Clear-Host
                show-menu
            }
            2 {
                Clear-Host
                Write-Host "Intializing MAS. . ."
                
                try {
                    $powershellCommand = "Set-ExecutionPolicy Bypass -Scope Process -Force; irm https://get.activated.win | iex"
                    Write-Host "Executing PowerShell command: $powershellCommand"
                    
                    $process = Start-Process -FilePath "powershell.exe" -ArgumentList "-Command $powershellCommand" -Wait -PassThru -NoNewWindow
                    
                    if ($process.ExitCode -eq 0) {
                        Write-Host "Windows Activated completed successfully"
                    }
                    else {
                        Write-Host "Windows Activated failed with return code: $($process.ExitCode)"
                    }
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
show-menu

while ($true) {
    $choice = Read-Host " "
    if ($choice -match '^(1[0-2]|[1-9])$' ) {
        switch ($choice ) {
            1 {
                Clear-Host
                exit
            }
            2 {

                Clear-Host
                Write-Host "Installing: 7Zip . . ."
                # download 7zip
                Get-FileFromWeb -URL "https://github.com/FR33THYFR33THY/files/raw/main/7-Zip.exe" -File "$env:TEMP\7-Zip.exe"
                # install 7zip
                Start-Process -wait "$env:TEMP\7-Zip.exe" -ArgumentList "/S"
                show-menu

            }
            3 {
                show-launchers-menu

            }
            4 {

                Clear-Host
                Write-Host "Installing: Discord . . ."
                # download discord
                Get-FileFromWeb -URL "https://dl.discordapp.net/distro/app/stable/win/x86/1.0.9036/DiscordSetup.exe" -File "$env:TEMP\Discord.exe"
                # install discord
                Start-Process -wait "$env:TEMP\Discord.exe" -ArgumentList "/s"
                show-menu

            }
            5 {

                Clear-Host
                Write-Host "Installing: Spotify . . ."
                # download spotify
                Get-FileFromWeb -URL "https://download.scdn.co/SpotifySetup.exe" -File "$env:TEMP\Spotify.exe"
                # install spotify
                Start-Process "$env:TEMP\Spotify.exe"
                show-menu

            }
            6 {

                Clear-Host
                Write-Host "Installing: Escape From Tarkov . . ."
                # download escape from tarkov
                Get-FileFromWeb -URL "https://prod.escapefromtarkov.com/launcher/download" -File "$env:TEMP\Escape From Tarkov.exe"
                # install escape from tarkov
                Start-Process "$env:TEMP\Escape From Tarkov.exe"
                show-menu

            }

            7 {
                show-browser-menu
            }
            8 {

                Clear-Host
                Write-Host "Installing: League Of Legends . . ."
                # download league of legends
                Get-FileFromWeb -URL "https://lol.secure.dyn.riotcdn.net/channels/public/x/installer/current/live.na.exe" -File "$env:TEMP\League Of Legends.exe"
                # install league of legends
                Start-Process "$env:TEMP\League Of Legends.exe"
                show-menu

            }
            9 {

                Clear-Host
                Write-Host "Installing: Notepad ++ . . ."
                # download notepad ++
                Get-FileFromWeb -URL "https://github.com/FR33THYFR33THY/files/raw/main/Notepad%20++.exe" -File "$env:TEMP\Notepad ++.exe"
                # install notepad ++
                Start-Process -wait "$env:TEMP\Notepad ++.exe" -ArgumentList "/S"
                show-menu

            }
            10 {

                Clear-Host
                Write-Host "Installing: OBS Studio . . ."
                # download obs studio
                Get-FileFromWeb -URL "https://github.com/obsproject/obs-studio/releases/download/30.2.3/OBS-Studio-30.2.3-Windows-Installer.exe" -File "$env:TEMP\OBS Studio.exe"
                # install obs studio
                Start-Process -wait "$env:TEMP\OBS Studio.exe" -ArgumentList "/S"
                show-menu

            }
            11 {

                Clear-Host
                Write-Host "Installing: Roblox . . ."
                # download roblox
                Get-FileFromWeb -URL "https://www.roblox.com/download/client?os=win" -File "$env:TEMP\Roblox.exe"
                # install roblox
                Start-Process "$env:TEMP\Roblox.exe"
                show-menu

            }

            12 {

                Clear-Host
                Write-Host "Installing: Valorant . . ."
                # download valorant
                Get-FileFromWeb -URL "https://valorant.secure.dyn.riotcdn.net/channels/public/x/installer/current/live.live.ap.exe" -File "$env:TEMP\Valorant.exe"
                # install valorant
                Start-Process "$env:TEMP\Valorant.exe"
                show-menu

            }
            13 {
                Clear-Host
                Write-Host "Installing: Microsoft Office 2024 LSTC Edition . . ."
                $toolPath = "$env:TEMP\officedeploymenttool_18227-20162.exe"
                $configurationPath = "$env:TEMP\OfficeDeployment\configuration-Office365-x64.xml"
                # download microsoft office
                Get-FileFromWeb -URL "https://download.microsoft.com/download/2/7/A/27AF1BE6-DD20-4CB4-B154-EBAB8A7D4A7E/officedeploymenttool_18227-20162.exe" -File $toolPath

                # extract office deployment tool
                Start-Process -FilePath $toolPath -ArgumentList "/quiet /extract:$env:TEMP\OfficeDeployment" -Wait

                # create configuration file
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
  <AppSettings>
    <User Key="software\microsoft\office\16.0\excel\options" Name="defaultformat" Value="51" Type="REG_DWORD" App="excel16" Id="L_SaveExcelfilesas" />
    <User Key="software\microsoft\office\16.0\powerpoint\options" Name="defaultformat" Value="27" Type="REG_DWORD" App="ppt16" Id="L_SavePowerPointfilesas" />
    <User Key="software\microsoft\office\16.0\word\options" Name="defaultformat" Value="" Type="REG_SZ" App="word16" Id="L_SaveWordfilesas" />
  </AppSettings>
</Configuration>
"@
                $configureOffice | Set-Content -Path $configurationPath -Force
                # install microsoft office
                Start-Process -FilePath "$env:TEMP\OfficeDeployment\setup.exe" -ArgumentList "/configure $configurationPath" -Wait
                # activating microsoft office
                Write-Host "Activating Microsoft Office . . ."
                $officePaths = @(
                    "$env:ProgramFiles(x86)\Microsoft Office\Office16",
                    "$env:ProgramFiles\Microsoft Office\Office16"
                )

                foreach ($path in $officePaths) {
                    if (Test-Path $path) {
                        Set-Location -Path $path
                        $licenseFiles = Get-ChildItem -Path "..\root\Licenses16\ProPlus2021VL_KMS*.xrm-ms"
                        foreach ($file in $licenseFiles) {
                            Start-Process -FilePath "cscript.exe" -ArgumentList "ospp.vbs /inslic:`"$file`"" -Wait
                        }
                        Start-Process -FilePath "cscript.exe" -ArgumentList "ospp.vbs /setprt:1688" -Wait
                        Start-Process -FilePath "cscript.exe" -ArgumentList "ospp.vbs /unpkey:6F7TH >nul" -Wait
                        Start-Process -FilePath "cscript.exe" -ArgumentList "ospp.vbs /inpkey:FXYTK-NJJ8C-GB6DW-3DYQT-6F7TH" -Wait
                        Start-Process -FilePath "cscript.exe" -ArgumentList "ospp.vbs /sethst:107.175.77.7" -Wait
                        Start-Process -FilePath "cscript.exe" -ArgumentList "ospp.vbs /act" -Wait
                    }
                }
                show-menu
            }
            14 {
                show-miscellaneous-menu
            }

        }
    }
    else { Write-Host "Invalid input. Please select a valid option (1 - 12)." }
}
