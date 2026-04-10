import sys
import os
import subprocess
import tempfile
import logging
import winreg
import time
import json
import threading

# Importar las nuevas utilidades
from .utils import (
    download_with_ssl,
    get_secure_temp_dir,
    handle_error,
)

LOG_FILE = "ztalon.txt"
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filemode='a'
)

def log_and_print(message):
    """Enhanced logging with both file and console output"""
    logging.info(message)
    print(message)

def show_error_popup(message, allow_continue=True):
    """Show error popup with option to continue or exit"""
    print(f"\n❌ ERROR: {message}")
    if allow_continue:
        choice = input("Press Enter to continue or 'q' to quit: ").lower()
        if choice == 'q':
            sys.exit(1)
    else:
        input("Press Enter to exit...")
        sys.exit(1)

def run_powershell_with_monitoring(command, script_path=None, timeout=300):
    """Run PowerShell command with clean logging"""
    try:
        cmd = None
        if script_path:
            cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-File", script_path]
            script_name = script_path.split('\\')[-1] if '\\' in script_path else script_path
            log_and_print(f"🔄 Executing script: {script_name}")
        elif command:
            cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-Command", command]
            log_and_print("🔄 Executing PowerShell command")
        else:
            log_and_print("❌ No PowerShell script path or command provided")
            return False
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Monitor output pero NO logear todo el stdout/stderr
        def read_output_silent(pipe):
            """Read output without logging everything"""
            for line in iter(pipe.readline, ''):
                # Solo mostrar en consola, no en logs
                if line.strip():
                    print(line.strip())
        
        stdout_thread = threading.Thread(target=read_output_silent, args=(process.stdout,))
        stderr_thread = threading.Thread(target=read_output_silent, args=(process.stderr,))
        
        stdout_thread.daemon = True
        stderr_thread.daemon = True
        
        stdout_thread.start()
        stderr_thread.start()
        
        # Wait for completion with timeout
        try:
            return_code = process.wait(timeout=timeout)
            stdout_thread.join(timeout=5)
            stderr_thread.join(timeout=5)
            
            if return_code == 0:
                log_and_print("✅ Script executed successfully")
                return True
            else:
                log_and_print(f"⚠️ Script finished with return code: {return_code}")
                return False
                
        except subprocess.TimeoutExpired:
            log_and_print(f"❌ Script timed out after {timeout} seconds")
            process.kill()
            process.wait()
            return False
            
    except Exception as e:
        log_and_print(f"❌ Error executing script: {e}")
        return False

def set_registry_value(root_key, key_path, value_name, value, value_type):
    """Safely set registry value with error handling"""
    try:
        # Open or create the key
        key = winreg.OpenKey(root_key, key_path, 0, winreg.KEY_WRITE)
        if key is None:
            key = winreg.CreateKey(root_key, key_path)
        
        # Set the value
        winreg.SetValueEx(key, value_name, 0, value_type, value)
        winreg.CloseKey(key)
        
        log_and_print(f"✅ Registry value set: {key_path}\\{value_name} = {value}")
        return True
        
    except Exception as e:
        log_and_print(f"❌ Failed to set registry value {key_path}\\{value_name}: {e}")
        return False

def apply_registry_changes(interactive=True, taskbar_alignment=None, apply_black_taskbar=None):
    """
    Apply system registry changes.
    
    Args:
        interactive (bool): If True, asks user for input via CLI. If False, uses provided arguments.
        taskbar_alignment (int): 0 for Left, 1 for Center. Required if interactive=False.
        apply_black_taskbar (bool): True to apply black taskbar settings. Required if interactive=False.
    """
    log_and_print("🔧 Applying registry changes...")

    def input_fn(prompt, default):
        return input(prompt) or default

    try:
        from init import safe_input as imported_safe_input
        input_fn = imported_safe_input
    except Exception:
        pass
    
    if interactive:
        # Prompt for taskbar position preference
        print("\n" + "="*60)
        print("                TASKBAR POSITION OPTION")
        print("="*60)
        print()
        print("Where do you want the taskbar icons to be positioned?")
        print()
        print("1. Left (classic position)")
        print("2. Center (Windows 11 default)")
        print()
        
        position_choice = input_fn("Enter your choice (1-2): ", "1").strip()
        
        # Configure taskbar alignment: 0 = Left, 1 = Center
        taskbar_alignment = 1 if position_choice == "2" else 0
        
        # Prompt for taskbar color customization
        print("\n" + "="*60)
        print("                TASKBAR COLOR OPTION")
        print("="*60)
        print()
        print("Do you want to set the taskbar to black color?")
        print("⚠️  (This may cause visual issues on some systems)")
        print()
        print("1. Yes, apply black taskbar")
        print("2. No, keep current colors")
        print()
        
        taskbar_choice = input_fn("Enter your choice (1-2): ", "2").strip()
        
        apply_black_taskbar = taskbar_choice == "1"
    else:
        # Validate arguments for non-interactive mode
        if taskbar_alignment is None:
            taskbar_alignment = 0 # Default to Left
        if apply_black_taskbar is None:
            apply_black_taskbar = False # Default to No

    # Core system registry modifications
    registry_modifications = [
        # Taskbar configuration
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "TaskbarAl", winreg.REG_DWORD, taskbar_alignment),
        # Dark theme enforcement
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize", "AppsUseLightTheme", winreg.REG_DWORD, 0),
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize", "SystemUsesLightTheme", winreg.REG_DWORD, 0),
        # Game DVR disable
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\GameDVR", "AppCaptureEnabled", winreg.REG_DWORD, 0),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\PolicyManager\default\ApplicationManagement\AllowGameDVR", "Value", winreg.REG_DWORD, 0),
        # Performance improvements
        (winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop", "MenuShowDelay", winreg.REG_SZ, "0"),
        (winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop\WindowMetrics", "MinAnimate", winreg.REG_DWORD, 0),
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "ExtendedUIHoverTime", winreg.REG_DWORD, 1),
        # File extension visibility
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "HideFileExt", winreg.REG_DWORD, 0),
        # Disable AI integrations (Talon 2.1.0 feature)
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Notepad", "DisableAI", winreg.REG_DWORD, 1),
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Paint", "DisableAI", winreg.REG_DWORD, 1),
        # Disable Office 365 ads in Settings (Talon 2.1.0 feature)
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager", "SubscribedContent-310093Enabled", winreg.REG_DWORD, 0),
    ]
    
    # Log user configuration choices
    position_text = "center" if taskbar_alignment == 1 else "left"
    log_and_print(f"📍 Taskbar position set to: {position_text}")
    
    # Apply black taskbar customizations if requested
    if apply_black_taskbar:
        log_and_print("🎨 Adding black taskbar configuration...")
        taskbar_modifications = [
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Accent", "AccentColorMenu", winreg.REG_DWORD, 1),
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize", "ColorPrevalence", winreg.REG_DWORD, 1),
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\DWM", "AccentColorInStartAndTaskbar", winreg.REG_DWORD, 1),
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Accent", "AccentPalette", winreg.REG_BINARY, b"\x00" * 32),
        ]
        registry_modifications.extend(taskbar_modifications)
    else:
        log_and_print("⚪ Skipping black taskbar configuration (user choice)")
    
    # Execute registry modifications
    successful = 0
    total_modifications = len(registry_modifications)
    
    for root_key, key_path, value_name, value_type, value in registry_modifications:
        if set_registry_value(root_key, key_path, value_name, value, value_type):
            successful += 1
    
    log_and_print(f"📊 Registry changes: {successful}/{total_modifications} applied successfully")
    
    # Warn about incomplete black taskbar application
    if apply_black_taskbar and successful < total_modifications:
        log_and_print("⚠️ Some black taskbar settings may not have been applied correctly")
        log_and_print("💡 You can manually change taskbar colors in Windows Settings > Personalization")
    
    # Restart Explorer to apply visual changes immediately
    try:
        log_and_print("🔄 Restarting Explorer to apply changes...")
        subprocess.run(["taskkill", "/F", "/IM", "explorer.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2)
        subprocess.run(["start", "explorer.exe"], shell=True)
        log_and_print("✅ Explorer restarted successfully")
        
        # Confirm applied changes
        log_and_print(f"📍 Taskbar positioned to the {position_text}")
        if apply_black_taskbar:
            log_and_print("🎨 Black taskbar settings applied - restart may be needed for full effect")
            
    except Exception as e:
        log_and_print(f"⚠️ Could not restart Explorer: {e}")
        if apply_black_taskbar:
            log_and_print("⚠️ Black taskbar settings may not take effect until manual restart")

def replace_command_in_script(script_path, replace_commands):
    """Replace commands in PowerShell script with clean logging"""
    try:
        with open(script_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Apply replacements
        for old_command, new_command in replace_commands.items():
            if old_command in content:
                content = content.replace(old_command, new_command)
        
        with open(script_path, 'w', encoding='utf-8') as file:
            file.write(content)
        
        return True
    except Exception as e:
        log_and_print(f"❌ Error modifying script: {e}")
        return False

@handle_error
def download_and_execute_script(script_url, script_name, replace_commands=None, timeout=300):

    import os
    import subprocess

    temp_dir = get_secure_temp_dir()
    script_path = os.path.join(temp_dir, script_name)

    if not download_with_ssl(script_url, script_path, timeout=timeout):
        log_and_print(f"❌ Error al descargar el script: {script_url}")
        return False

    if replace_commands:
        try:
            with open(script_path, "r", encoding="utf-8") as f:
                content = f.read()
            for old, new in replace_commands.items():
                content = content.replace(old, new)
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            log_and_print(f"❌ Error al modificar el script: {e}")
            return False

    try:
        subprocess.run(
            ["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", script_path],
            check=True,
            timeout=timeout
        )
        log_and_print(f"✅ Script ejecutado correctamente: {script_name}")
        return True
    except subprocess.CalledProcessError as e:
        log_and_print(f"❌ Error al ejecutar el script: {e}")
        return False
    except subprocess.TimeoutExpired:
        log_and_print(f"❌ El script tardó demasiado y fue cancelado: {script_name}")
        return False

def install_timerresolution():
    """Install Timer Resolution with enhanced error handling"""
    log_and_print("⏱️ Starting Timer Resolution installation...")
    script_url = "https://raw.githubusercontent.com/FR33THYFR33THY/Ultimate/main/6%20Windows/30%20Timer%20Resolution.ps1"
    replace_commands = {'$choice = Read-Host " "': '$choice = 1'}
    return download_and_execute_script(script_url, "TimerResolution.ps1", replace_commands)

def run_startmenuoptimization():
    """Optimize start menu with fallback to manual registry tweaks"""
    log_and_print("🎯 Starting start menu optimization...")
    
    # Try multiple URLs for the script
    script_urls = [
        "https://raw.githubusercontent.com/FR33THYFR33THY/Ultimate/main/6%20Windows/1%20Start%20Menu%20Taskbar.ps1"
    ]
    
    replace_commands = {'$choice = Read-Host " "': '$choice = 1'}
    
    # Attempt download from each URL
    for i, script_url in enumerate(script_urls, 1):
        log_and_print(f"🔄 Attempting download from URL {i}/{len(script_urls)}")
        
        if download_and_execute_script(script_url, "Startmenu.ps1", replace_commands):
            return True
        
        if i < len(script_urls):
            log_and_print(f"⚠️ URL {i} failed, trying alternative...")
    
    # Fallback to manual registry modifications
    log_and_print("⚠️ All download attempts failed, applying manual start menu optimizations...")
    
    try:
        # Manual start menu and taskbar optimizations
        manual_optimizations = [
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "Start_ShowClassicMode", winreg.REG_DWORD, 1),
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "StartMenuAdminTools", winreg.REG_DWORD, 1),
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "StartShownOnUpgrade", winreg.REG_DWORD, 1),
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "ShowTaskViewButton", winreg.REG_DWORD, 0),
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Search", "SearchboxTaskbarMode", winreg.REG_DWORD, 0),
        ]
        
        successful = 0
        for root_key, key_path, value_name, value_type, value in manual_optimizations:
            if set_registry_value(root_key, key_path, value_name, value, value_type):
                successful += 1
        
        log_and_print(f"📊 Manual start menu optimizations: {successful}/{len(manual_optimizations)} applied")
        return successful > 0
        
    except Exception as e:
        log_and_print(f"❌ Error in manual start menu optimization: {e}")
        return False

def run_autoruns():
    """Optimize autoruns with enhanced error handling"""
    log_and_print("🚀 Starting autoruns optimization...")
    script_url = "https://raw.githubusercontent.com/FR33THYFR33THY/Ultimate/main/6%20Windows/34%20Autoruns%20Startup%20Tasks%20%26%20Apps%20Check.ps1"
    return download_and_execute_script(script_url, "Autoruns.ps1")

def run_backgroundapps():
    """Optimize background apps with enhanced error handling"""
    log_and_print("📱 Starting background apps optimization...")
    script_url = "https://raw.githubusercontent.com/FR33THYFR33THY/Ultimate/main/3%20Setup/9%20Background%20Apps.ps1"
    replace_commands = {'$choice = Read-Host " "': '$choice = 1'}
    return download_and_execute_script(script_url, "BackgroundApps.ps1", replace_commands)

def run_copilotuninstaller():
    """Uninstall Copilot with enhanced error handling"""
    log_and_print("🤖 Starting Copilot uninstallation...")
    script_url = "https://raw.githubusercontent.com/FR33THYFR33THY/Ultimate/main/6%20Windows/9%20Copilot.ps1"
    replace_commands = {'$choice = Read-Host " "': '$choice = 1'}
    return download_and_execute_script(script_url, "copilotuninstaller.ps1", replace_commands)

def run_widgetsuninstaller():
    """Uninstall Widgets with enhanced error handling"""
    log_and_print("🧩 Starting Widgets uninstallation...")
    script_url = "https://raw.githubusercontent.com/FR33THYFR33THY/Ultimate/main/6%20Windows/8%20Widgets.ps1"
    replace_commands = {'$choice = Read-Host " "': '$choice = 1'}
    return download_and_execute_script(script_url, "widgetsuninstaller.ps1", replace_commands)

def run_gamebaroptimization():
    """Optimize GameBar with enhanced error handling"""
    log_and_print("🎮 Starting GameBar optimization...")
    script_url = "https://raw.githubusercontent.com/FR33THYFR33THY/Ultimate/main/6%20Windows/19%20Gamebar.ps1"
    replace_commands = {'$choice = Read-Host " "': '$choice = 1'}
    return download_and_execute_script(script_url, "gamebar.ps1", replace_commands)

def apply_powerplan():
    """Apply power plan optimization with enhanced error handling"""
    log_and_print("⚡ Starting power plan optimization...")
    script_url = "https://raw.githubusercontent.com/FR33THYFR33THY/Ultimate/main/6%20Windows/29%20Power%20Plan.ps1"
    replace_commands = {'$choice = Read-Host " "': '$choice = 1'}
    return download_and_execute_script(script_url, "powerplan.ps1", replace_commands)

def apply_signoutlockscreen():
    """Optimize lock screen with enhanced error handling"""
    log_and_print("🔒 Starting lock screen optimization...")
    script_url = "https://raw.githubusercontent.com/FR33THYFR33THY/Ultimate/main/6%20Windows/6%20Signout%20Lockscreen%20Wallpaper%20Black.ps1"
    replace_commands = {'$choice = Read-Host " "': '$choice = 1'}
    return download_and_execute_script(script_url, "lockscreensignout.ps1", replace_commands)

def run_edgeuninstaller():
    """Uninstall Edge with enhanced error handling"""
    log_and_print("🌐 Starting Edge uninstallation...")
    script_url = "https://raw.githubusercontent.com/FR33THYFR33THY/Ultimate/main/6%20Windows/20%20Edge%20%26%20WebView.ps1"
    replace_commands = {'$choice = Read-Host " "': '$choice = 1'}
    return download_and_execute_script(script_url, "edgeuninstaller.ps1", replace_commands)

def apply_networkoptimization():
    """Apply network optimization with split scripts"""
    log_and_print("🌐 Starting network optimization...")
    replace_commands = {'$choice = Read-Host " "': '$choice = 1'}
    first_url = "https://raw.githubusercontent.com/FR33THYFR33THY/Ultimate/main/6%20Windows/26%20Network%20Adapter%20Power%20Savings%20%26%20Wake.ps1"
    second_url = "https://raw.githubusercontent.com/FR33THYFR33THY/Ultimate/main/6%20Windows/27%20Network%20IPv4%20Only.ps1"

    first_ok = download_and_execute_script(first_url, "network_adapter_power_wake.ps1", replace_commands)
    second_ok = download_and_execute_script(second_url, "network_ipv4_only.ps1", replace_commands)
    return first_ok and second_ok

def apply_msimode():
    """Apply MSI mode optimization with enhanced error handling"""
    log_and_print("🔧 Starting MSI mode optimization...")
    script_url = "https://raw.githubusercontent.com/FR33THYFR33THY/Ultimate/main/5%20Graphics/9%20Msi%20Mode.ps1"
    replace_commands = {'$choice = Read-Host " "': '$choice = 1'}
    return download_and_execute_script(script_url, "msimode.ps1", replace_commands)

def run_directxinstallation():
    """Install DirectX with enhanced error handling"""
    log_and_print("📊 Starting DirectX installation...")
    script_url = "https://raw.githubusercontent.com/FR33THYFR33THY/Ultimate/main/5%20Graphics/10%20DirectX.ps1"
    return download_and_execute_script(script_url, "directx.ps1", timeout=600)  # Longer timeout for installation

def run_cinstallation():
    """Install C++ redistributables with enhanced error handling"""
    log_and_print("🔧 Starting C++ redistributables installation...")
    script_url = "https://raw.githubusercontent.com/FR33THYFR33THY/Ultimate/main/5%20Graphics/11%20C%2B%2B.ps1"
    return download_and_execute_script(script_url, "c++.ps1", timeout=600)  # Longer timeout for installation

def apply_amdoptimization():
    """Apply AMD optimizations with enhanced error handling"""
    log_and_print("🔴 Starting AMD optimization...")
    script_url = "https://raw.githubusercontent.com/FR33THYFR33THY/Ultimate/main/5%20Graphics/5%20Amd%20Settings.ps1"
    replace_commands = {
        '$choice = Read-Host " "': '$choice = 1',
        'shutdown -r -t 00': 'Write-Host "Skipping automatic reboot (patched mode)"',
        'Restart-Computer': 'Write-Host "Skipping Restart-Computer (patched mode)"',
    }
    return download_and_execute_script(script_url, "amdsettings.ps1", replace_commands)

def run_driver_debloat_settings_amd():
    """Run graphics driver debloat/settings script in AMD debloat/settings mode."""
    log_and_print("🧰 Starting driver debloat/settings (AMD mode)...")
    script_url = "https://raw.githubusercontent.com/FR33THYFR33THY/Ultimate/main/5%20Graphics/3%20Driver%20Install%20Debloat%20%26%20Settings.ps1"
    replace_commands = {
        '$choice = Read-Host " "': '$choice = "2"',
        'Pause': 'Write-Host "Skipping pause in automated mode"',
        'Start-Process "https://www.amd.com/en/support/download/drivers.html"': 'Write-Host "Skipping AMD driver download (patched mode)"',
        'Add-Type -AssemblyName System.Windows.Forms': 'Write-Host "Skipping OpenFileDialog in patched mode"',
        '$Dialog = New-Object System.Windows.Forms.OpenFileDialog': '$InstallFile = $null',
        '$Dialog.Filter = "All Files (*.*)|*.*"': '$InstallFile = $null',
        '$Dialog.ShowDialog() | Out-Null': 'Write-Host "Skipping file picker (patched mode)"',
        '$InstallFile = $Dialog.FileName': '$InstallFile = $null',
        '& "$env:SystemDrive\\Program Files\\7-Zip\\7z.exe" x "$InstallFile" -o"$env:SystemRoot\\Temp\\amddriver" -y | Out-Null': 'Write-Host "Skipping AMD driver extraction (patched mode)"',
        'Start-Process -Wait "$env:SystemRoot\\Temp\\amddriver\\Bin64\\ATISetup.exe" -ArgumentList "-INSTALL -VIEW:2" -WindowStyle Hidden': 'Write-Host "Skipping AMD driver installer launch (patched mode)"',
        'Remove-Item "$InstallFile" -Force -ErrorAction SilentlyContinue | Out-Null': 'Write-Host "Skipping installer file removal (patched mode)"',
        'shutdown -r -t 00': 'Write-Host "Skipping automatic reboot (patched mode)"',
        'Restart-Computer': 'Write-Host "Skipping Restart-Computer (patched mode)"',
    }
    return download_and_execute_script(script_url, "driver_debloat_settings.ps1", replace_commands, timeout=1800)

def run_spectre_meltdown():
    """Apply Spectre/Meltdown mitigations"""
    log_and_print("🛡️ Starting Spectre/Meltdown optimization...")
    script_url = "https://raw.githubusercontent.com/FR33THYFR33THY/Ultimate/main/8%20Advanced/3%20Spectre%20Meltdown.ps1"
    replace_commands = {'$choice = Read-Host " "': '$choice = 1'}
    return download_and_execute_script(script_url, "spectre_meltdown.ps1", replace_commands)

def run_uac_optimization():
    """Apply UAC optimization"""
    log_and_print("🔐 Starting UAC optimization...")
    script_url = "https://raw.githubusercontent.com/FR33THYFR33THY/Ultimate/main/6%20Windows/31%20UAC.ps1"
    replace_commands = {'$choice = Read-Host " "': '$choice = 1'}
    return download_and_execute_script(script_url, "uac.ps1", replace_commands)

def run_core_isolation_optimization():
    """Apply Core Isolation optimization"""
    log_and_print("🧱 Starting Core Isolation optimization...")
    script_url = "https://raw.githubusercontent.com/FR33THYFR33THY/Ultimate/main/6%20Windows/32%20Core%20Isolation.ps1"
    replace_commands = {'$choice = Read-Host " "': '$choice = 1'}
    return download_and_execute_script(script_url, "core_isolation.ps1", replace_commands)

def run_defender_optimize():
    """Apply Defender optimization"""
    log_and_print("🛡️ Starting Defender optimization...")
    script_url = "https://raw.githubusercontent.com/FR33THYFR33THY/Ultimate/main/6%20Windows/33%20Defender%20Optimize.ps1"
    replace_commands = {'$choice = Read-Host " "': '$choice = 1'}
    return download_and_execute_script(script_url, "defender_optimize.ps1", replace_commands)

def get_gpu_info_advanced():
    """
    Get advanced GPU information using PowerShell and WMI.
    Returns a list of dictionaries containing GPU details.
    """
    try:
        cmd = [
            "powershell", "-NoProfile", "-Command",
            "Get-CimInstance Win32_VideoController | Select-Object Name, DriverVersion, VideoProcessor, AdapterRAM | ConvertTo-Json -Compress"
        ]
        
        # Run command with creationflags to hide window
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            startupinfo=startupinfo
        )
        stdout, stderr = process.communicate(timeout=10)
        
        if process.returncode != 0:
            log_and_print(f"⚠️ Error getting GPU info: {stderr}")
            return []
            
        if not stdout.strip():
            return []
            
        # Parse JSON output
        data = json.loads(stdout)
        
        # Handle single object vs list
        if isinstance(data, dict):
            data = [data]
            
        gpu_info = []
        for item in data:
            name = item.get('Name', 'Unknown GPU')
            driver = item.get('DriverVersion', 'Unknown')
            processor = item.get('VideoProcessor', 'Unknown')
            
            # Determine type based on name
            gpu_type = "Unknown"
            name_lower = name.lower()
            if "amd" in name_lower or "radeon" in name_lower:
                gpu_type = "AMD"
                
            gpu_info.append({
                'name': name,
                'type': gpu_type,
                'driver_version': driver,
                'processor': processor
            })
            
        return gpu_info
        
    except Exception as e:
        log_and_print(f"❌ Failed to get GPU info: {e}")
        return []

def apply_gpuregistryoptimization(gpu_info):
    """Apply GPU-specific registry optimizations"""
    try:
        # Handle both list and string inputs
        if isinstance(gpu_info, list):
            if gpu_info and len(gpu_info) > 0:
                # Get the type from the first GPU in the list
                gpu_type = gpu_info[0].get('type', 'Unknown') if isinstance(gpu_info[0], dict) else str(gpu_info[0])
                gpu_name = gpu_info[0].get('name', 'Unknown GPU') if isinstance(gpu_info[0], dict) else str(gpu_info[0])
                log_and_print(f"🎯 Applying GPU registry optimizations for: {gpu_name} ({gpu_type})")
            else:
                log_and_print("⚠️ No GPU information available, applying generic optimizations")
                gpu_type = "unknown"
        else:
            # Handle string input (backward compatibility)
            gpu_type = str(gpu_info)
            log_and_print(f"🎯 Applying GPU registry optimizations for: {gpu_type}")
        
        # Convert to lowercase for comparison
        gpu_type_lower = gpu_type.lower()
        
        if "amd" in gpu_type_lower:
            log_and_print("🔴 Applying AMD-specific registry optimizations...")
            registry_modifications = [
                # AMD-specific optimizations
                (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}\0000", "EnableUlps", winreg.REG_DWORD, 0),
                (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}\0000", "PP_ThermalAutoThrottlingEnable", winreg.REG_DWORD, 0),
                (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}\0000", "DisableDMACopy", winreg.REG_DWORD, 1),
                (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}\0000", "DisableBlockWrite", winreg.REG_DWORD, 0),
            ]
        else:
            log_and_print("🔧 Applying generic GPU optimizations...")
            registry_modifications = [
                # Generic GPU optimizations
                (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers", "TdrDelay", winreg.REG_DWORD, 8),
                (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers", "TdrDdiDelay", winreg.REG_DWORD, 8),
                (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers", "TdrLevel", winreg.REG_DWORD, 0),
            ]
        
        # Apply registry modifications
        successful = 0
        total_modifications = len(registry_modifications)
        
        for root_key, key_path, value_name, value_type, value in registry_modifications:
            if set_registry_value(root_key, key_path, value_name, value, value_type):
                successful += 1
        
        log_and_print(f"📊 GPU optimizations: {successful}/{total_modifications} applied successfully")
        
        if successful == total_modifications:
            log_and_print("✅ All GPU registry optimizations applied successfully")
            return True
        elif successful > 0:
            log_and_print(f"⚠️ Partial success: {successful}/{total_modifications} GPU optimizations applied")
            return True
        else:
            log_and_print("❌ No GPU optimizations could be applied")
            return False
            
    except Exception as e:
        log_and_print(f"❌ Error applying GPU registry optimizations: {e}")
        return False

def run_external_debloat_scripts():
    """Run external debloat scripts with enhanced monitoring"""
    log_and_print("🧹 Starting external debloat scripts...")
    
    scripts = [
        {
            "name": "ChrisTitusTech WinUtil",
            # Usar GitHub directamente en lugar del redirect
            "command": 'irm https://christitus.com/win | iex',
            "timeout": 1800
        },
        {
            "name": "Raphi Win11Debloat",
            "command": '& ([scriptblock]::Create((irm "https://debloat.raphi.re/"))) -Silent -RemoveApps -RemoveGamingApps -DisableTelemetry -DisableBing -DisableSuggestions -DisableLockscreenTips -RevertContextMenu -TaskbarAlignLeft -HideSearchTb -DisableWidgets -DisableCopilot -ClearStartAllUsers -DisableDVR -DisableStartRecommended -ExplorerToThisPC -DisableMouseAcceleration',
            "timeout": 1200
        }
    ]
    
    for script in scripts:
        try:
            log_and_print(f"🚀 Running {script['name']}...")
            log_and_print("⚠️ Note: This script will run interactively. Follow the on-screen instructions.")
            
            # Execute the script
            success = run_powershell_with_monitoring(script['command'], timeout=script['timeout'])
            
            if success:
                log_and_print(f"✅ {script['name']} completed successfully")
            else:
                log_and_print(f"⚠️ {script['name']} had issues")
                
        except Exception as e:
            log_and_print(f"❌ Error running {script['name']}: {e}")
    
    log_and_print("✅ External debloat scripts completed")

def run_advanced_cleanup():
    """Advanced cleanup using integrated PowerShell script"""
    log_and_print("🧹 Starting advanced system cleanup...")
    
    # Enhanced cleanup script combining the best of all methods
    cleanup_script = """
    # Enhanced ZTalon Cleanup Script
    Write-Host "🗑️ Starting comprehensive cleanup..." -ForegroundColor Green
    
    # Function to safely remove and recreate directories
    function Clean-Directory {
        param([string]$Path, [string]$Name)
        try {
            if (Test-Path $Path) {
                Write-Host "🧹 Cleaning $Name..." -ForegroundColor Yellow
                Remove-Item -Path $Path -Recurse -Force -ErrorAction SilentlyContinue | Out-Null
                New-Item -Path (Split-Path $Path -Parent) -Name (Split-Path $Path -Leaf) -ItemType Directory -ErrorAction SilentlyContinue | Out-Null
                Write-Host "✅ $Name cleaned successfully" -ForegroundColor Green
            }
        } catch {
            Write-Host "⚠️ Could not clean $Name : $_" -ForegroundColor Red
        }
    }
    
    # Clean user temp directory
    Clean-Directory "$env:USERPROFILE\\AppData\\Local\\Temp" "User Temp"
    
    # Clean system temp directory  
    Clean-Directory "$env:SystemDrive\\Windows\\Temp" "System Temp"
    
    # Clean prefetch directory
    Clean-Directory "$env:SystemDrive\\Windows\\Prefetch" "Prefetch Cache"
    
    # Additional cleanup locations
    $additional_paths = @(
        "$env:LOCALAPPDATA\\Microsoft\\Windows\\INetCache",
        "$env:LOCALAPPDATA\\Microsoft\\Windows\\WebCache", 
        "$env:SystemDrive\\Windows\\SoftwareDistribution\\Download",
        "$env:SystemRoot\\Logs"
    )
    
    foreach ($path in $additional_paths) {
        if (Test-Path $path) {
            try {
                Write-Host "🧹 Cleaning $(Split-Path $path -Leaf)..." -ForegroundColor Yellow
                Get-ChildItem -Path $path -Recurse -Force -ErrorAction SilentlyContinue | Remove-Item -Force -Recurse -ErrorAction SilentlyContinue
                Write-Host "✅ $(Split-Path $path -Leaf) cleaned" -ForegroundColor Green
            } catch {
                Write-Host "⚠️ Could not clean $(Split-Path $path -Leaf)" -ForegroundColor Red
            }
        }
    }
    
    Write-Host "🎉 Advanced cleanup completed!" -ForegroundColor Green
    """
    
    script_path: str | None = None
    try:
        # Write the script to temp file
        temp_dir = tempfile.gettempdir()
        script_path = os.path.join(temp_dir, "ztalon_advanced_cleanup.ps1")
        
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(cleanup_script)
        
        # Execute the enhanced cleanup script
        if run_powershell_with_monitoring(None, script_path, timeout=180):
            log_and_print("✅ Advanced cleanup completed successfully")
            return True
        else:
            log_and_print("⚠️ Advanced cleanup had some issues")
            return False
            
    except Exception as e:
        log_and_print(f"❌ Error during advanced cleanup: {e}")
        return False
    finally:
        # Clean up the script file
        try:
            if script_path is not None and os.path.exists(script_path):
                os.remove(script_path)
        except Exception:
            pass

def disable_wpbt():
    """Disable Windows Platform Binary Table (WPBT) for security"""
    try:
        key_path = r"SYSTEM\CurrentControlSet\Control\FirmwareResources\{B9816C50-7A49-4A2A-8B2E-5A6E2E7B82B6}"
        winreg.DeleteKey(winreg.HKEY_LOCAL_MACHINE, key_path)
        log_and_print("✅ WPBT successfully disabled.")
        return True
    except FileNotFoundError:
        log_and_print("⚠️ WPBT key not found or already disabled.")
        return True
    except Exception as e:
        log_and_print(f"❌ Could not disable WPBT: {e}")
        return False

def disable_folder_discovery():
    """Disable automatic folder type discovery in File Explorer"""
    try:
        # Remove AllFolders property if exists
        bags_key = r"Software\Classes\Local Settings\Software\Microsoft\Windows\Shell\Bags"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, bags_key, 0, winreg.KEY_SET_VALUE) as key:
            try:
                winreg.DeleteValue(key, "AllFolders")
            except FileNotFoundError:
                pass  # Already removed

        # Set FolderType to NotSpecified
        shell_key = r"Software\Classes\Local Settings\Software\Microsoft\Windows\Shell\Bags\AllFolders\Shell"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, shell_key) as key:
            winreg.SetValueEx(key, "FolderType", 0, winreg.REG_SZ, "NotSpecified")

        log_and_print("✅ Automatic folder type discovery disabled.")
        return True
    except Exception as e:
        log_and_print(f"❌ Could not disable folder discovery: {e}")
        return False

def run_final_cleanup():
    """Final cleanup with all methods combined"""
    log_and_print("🧹 Starting comprehensive final cleanup...")
    
    # Run the existing online cleanup script
    script_url = "https://raw.githubusercontent.com/FR33THYFR33THY/Ultimate/main/6%20Windows/35%20Cleanup.ps1"
    
    online_success = download_and_execute_script(script_url, "Cleanup.ps1")
    
    # Run our enhanced local cleanup
    local_success = run_advanced_cleanup()
    
    # Basic fallback cleanup
    try:
        log_and_print("🗑️ Running fallback cleanup...")
        temp_dirs = [
            os.environ.get("TEMP", ""),
            os.environ.get("TMP", ""), 
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Temp")
        ]
        
        for temp_dir in temp_dirs:
            if temp_dir and os.path.exists(temp_dir):
                try:
                    ztalon_temp = os.path.join(temp_dir, "ztalon")
                    if os.path.exists(ztalon_temp):
                        import shutil
                        shutil.rmtree(ztalon_temp, ignore_errors=True)
                        log_and_print(f"🗑️ Cleaned ZTalon temp files: {ztalon_temp}")
                except Exception as e:
                    log_and_print(f"⚠️ Could not clean {temp_dir}: {e}")
        
    except Exception as e:
        log_and_print(f"⚠️ Error during fallback cleanup: {e}")
    
    # Summary
    if online_success and local_success:
        log_and_print("🎉 All cleanup methods completed successfully")
    elif online_success or local_success:
        log_and_print("✅ Cleanup completed with some methods successful")
    else:
        log_and_print("⚠️ Cleanup completed but with issues - basic cleanup applied")

def finalize_installation():
    """Final cleanup using the comprehensive new cleaning system"""
    log_and_print("🎉 Starting final installation cleanup...")
    
    # Use the new comprehensive cleanup system that combines all methods
    log_and_print("🚀 Executing comprehensive cleanup system...")
    
    # Call the enhanced cleanup function that combines:
    # - Online cleanup script
    # - Advanced local cleanup (temp, prefetch, cache, etc.)
    # - Fallback basic cleanup
    run_final_cleanup()
    
    # Additional ZTalon-specific cleanup
    try:
        log_and_print("🧹 Performing final ZTalon cleanup...")
        
        # Clean any remaining ZTalon temporary files from all possible locations
        import shutil
        cleanup_locations = [
            os.environ.get("TEMP", ""),
            os.environ.get("TMP", ""),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Temp"),
            tempfile.gettempdir()
        ]
        
        for location in cleanup_locations:
            if location and os.path.exists(location):
                try:
                    ztalon_files = [
                        os.path.join(location, "ztalon"),
                        os.path.join(location, "ztalon_advanced_cleanup.ps1"),
                        os.path.join(location, "Registry.ps1"),
                        os.path.join(location, "TimerResolution.ps1"),
                        os.path.join(location, "Cleanup.ps1")
                    ]
                    
                    for ztalon_file in ztalon_files:
                        if os.path.exists(ztalon_file):
                            if os.path.isdir(ztalon_file):
                                shutil.rmtree(ztalon_file, ignore_errors=True)
                                log_and_print(f"🗑️ Removed directory: {ztalon_file}")
                            else:
                                os.remove(ztalon_file)
                                log_and_print(f"🗑️ Removed file: {ztalon_file}")
                                
                except Exception as e:
                    log_and_print(f"⚠️ Could not clean {location}: {e}")
        
        # Force garbage collection to free memory
        import gc
        gc.collect()
        
        log_and_print("✅ Final ZTalon cleanup completed")
        
    except Exception as e:
        log_and_print(f"⚠️ Error during final ZTalon cleanup: {e}")
    
    # Final summary
    log_and_print("🎊 Installation finalization completed!")
    log_and_print("📋 Summary of cleanup performed:")
    log_and_print("   ✅ Online cleanup script executed")
    log_and_print("   ✅ Advanced local cleanup (temp, prefetch, cache)")
    log_and_print("   ✅ ZTalon temporary files removed")
    log_and_print("   ✅ Memory cleanup performed")
    
    return True

